"""What a Lucidity run costs in model calls, and what that means per user per month.

Reads the run records (state/runs/*.json) and the per-call usage log (logs/usage.jsonl) on the machine that ran
them. Counts only finished live runs with the Built-in worker on tables: the four tabular demos and anything set
up through Bring a CSV (the text demos pay for a model inside their scorer too, which isn't the orchestrator's cost). Prints a markdown table. Usage:
    python evidence/tokenomics.py
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lucidity.cost import model_cost  # noqa: E402

runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "state" / "runs").glob("*.json"))]
TABLE_DEMOS = {"hoopkit", "fedkit", "creditkit", "stockkit"}
runs = [r for r in runs if r.get("worker") == "builtin" and not r.get("demo") and r["state"] == "done"
        and (r["repo_name"] in TABLE_DEMOS or "/state/csv/" in r["repo"].replace("\\", "/"))]
usage = [json.loads(line) for line in (ROOT / "logs" / "usage.jsonl").open(encoding="utf-8")]

rows = []
for r in runs:
    calls = [u for u in usage if r["started"] <= u["ts"] <= r["finished"]]
    inp, cached, out = (sum(u.get(k) or 0 for u in calls) for k in ("input_tokens", "cached_input_tokens", "output_tokens"))
    no_cache = model_cost(r["model"], inp, 0, out)          # same calls, if no input had been cached
    rows.append(dict(id=r["id"], repo=r["repo_name"], usd=r["spent_usd"], s=r["elapsed_s"], requests=sum(u.get("requests") or 1 for u in calls),
                     inp=inp, cached=cached, out=out, no_cache=no_cache, with_cache=model_cost(r["model"], inp, cached, out)))

print("| Run | Table | Model requests | Input tokens (cached) | Output tokens | Cost | Cost with no caching | Time |")
print("|---|---|---|---|---|---|---|---|")
for x in rows:
    print(f"| `{x['id']}` | {x['repo'].split('-')[0]} | {x['requests']} | {x['inp']:,} ({x['cached'] / max(x['inp'], 1):.0%}) | {x['out']:,} "
          f"| ${x['usd']:.4f} | ${x['no_cache']:.4f} | {x['s']:.0f} s |")

med = statistics.median(x["usd"] for x in rows)
hi = max(x["usd"] for x in rows)
saved = 1 - sum(x["with_cache"] for x in rows) / sum(x["no_cache"] for x in rows)
print(f"\n{len(rows)} runs. Median ${med:.4f} a run, most expensive ${hi:.4f}. Prompt caching cut the model bill by {saved:.0%}.\n")
print("| Runs a month per user | Per user | 100 users | 10,000 users |")
print("|---|---|---|---|")
for n in (5, 20, 100):
    print(f"| {n} at the median | ${n * med:.2f} | ${100 * n * med:,.2f} | ${10_000 * n * med:,.0f} |")
print(f"| 100 at the most expensive | ${100 * hi:.2f} | ${100 * 100 * hi:,.2f} | ${10_000 * 100 * hi:,.0f} |")
