"""Run the eval cases through the real pipeline under several configurations and write
evals/results.json, which the Evals tab shows. Every number in the file comes from this run.

    .venv/Scripts/python evals/run_evals.py
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evals.variants import build_cases  # noqa: E402
from lucidity import config, llm  # noqa: E402
from lucidity.agents import checker, coordinator  # noqa: E402
from lucidity.guard import breaker  # noqa: E402

OUT = ROOT / "evals" / "results.json"
CONFIGS = [
    ("default", "batches of 10 sessions per triage call, last 14 events each, unchanged sessions skipped",
     dict(tail=14, batch=True, skip_unchanged=True)),
    ("trimmed tail", "same, but only the last 6 events per session", dict(tail=6, batch=True, skip_unchanged=True)),
    ("long tail", "same, but the last 30 events per session", dict(tail=30, batch=True, skip_unchanged=True)),
    ("one call per session", "no batching: a triage call for every session", dict(tail=14, batch=False, skip_unchanged=True)),
    ("no change skip", "default, but every refresh re-reads every session (the bug that started the project)",
     dict(tail=14, batch=True, skip_unchanged=False)),
]
REPEATS = 3


def usage_since(mark):
    rows = []
    for line in llm.USAGE_LOG.read_text(encoding="utf-8").splitlines()[mark:]:
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def log_len():
    return len(llm.USAGE_LOG.read_text(encoding="utf-8").splitlines()) if llm.USAGE_LOG.exists() else 0


def score(cases, snap):
    rows = {r["id"]: r for r in snap["sessions"]}
    out = []
    for c in cases:
        e, r = c["expected"], rows[c["session"].id]
        got_flags = sorted(f["kind"] for f in r["flags"])
        verdict = (r.get("checker") or {}).get("verdict")
        checks = {"state": r["state"] == e["state"], "flags": got_flags == e["flags"],
                  "secrets": bool(r["secrets"]) == e["secrets"]}
        if e.get("checker") and r.get("checker"):
            checks["checker"] = verdict == e["checker"]
        out.append({"name": c["name"], "expected": e, "state": r["state"], "flags": got_flags,
                    "secrets": [s["kind"] for s in r["secrets"]], "checker": verdict,
                    "warning": r.get("warning", ""), "dropped_claims": r.get("dropped_claims", 0),
                    "overridden": r.get("overridden"), "claims": len(r["claims"]), "checks": checks,
                    "pass": all(checks.values())})
    return out


def run_once(name, opts, cases, with_checker):
    """A cold refresh (scored), then the same sessions again with nothing changed."""
    sessions = [c["session"] for c in cases]
    cache = config.STATE_DIR / f"eval_{name.replace(' ', '_')}.json"
    cache.unlink(missing_ok=True)
    o = lambda: coordinator.Options(mode="sample", cache_name=cache.stem, run_checker=with_checker, **opts)
    mark, t0 = log_len(), time.perf_counter()
    snap = coordinator.refresh(o(), sessions=sessions)
    secs = time.perf_counter() - t0
    rows = usage_since(mark)
    if snap.get("banner"):
        raise SystemExit(f"{name}: {snap['banner']}")
    mark2 = log_len()
    coordinator.refresh(o(), sessions=sessions)
    return {"cases": score(cases, snap), "rows": rows, "seconds": round(secs, 1), "repeat_rows": usage_since(mark2)}


def _span(vals, n=None):
    lo, hi = min(vals), max(vals)
    s = f"{lo}" if lo == hi else f"{lo}–{hi}"
    return f"{s}/{n}" if n is not None else s


def metrics(runs, with_checker):
    n = len(runs[0]["cases"])
    count = lambda key: [sum(c["checks"][key] for c in r["cases"]) for r in runs]
    inj = [[c for c in r["cases"] if c["expected"]["injection"]] for r in runs]
    m = {
        "state right": _span(count("state"), n),
        "flags right": _span(count("flags"), n),
        "secrets right": _span(count("secrets"), n),
        "injections noticed": _span([sum(bool(c["warning"]) for c in x) for x in inj], len(inj[0])),
        "claims dropped": _span([sum(c["dropped_claims"] for c in r["cases"]) for r in runs]),
        "model requests": _span([sum(x["requests"] for x in r["rows"]) for r in runs]),
        "tokens": round(sum(sum(x["input_tokens"] + x["output_tokens"] for x in r["rows"]) for r in runs) / len(runs)),
        "cost": f"${sum(sum(x['usd'] for x in r['rows']) for r in runs) / len(runs):.4f}",
        "seconds": round(sum(r["seconds"] for r in runs) / len(runs), 1),
        "repeat refresh requests": _span([sum(x["requests"] for x in r["repeat_rows"]) for r in runs]),
    }
    if with_checker:
        ch = [[c for c in r["cases"] if "checker" in c["checks"]] for r in runs]
        m["checker right"] = _span([sum(c["checks"]["checker"] for c in x) for x in ch], len(ch[0]))
    return m


def main():
    if not config.has_key():
        raise SystemExit("needs OPENAI_API_KEY")
    # this process only: room for the whole sweep; the breaker still applies
    breaker.daily_usd_cap = max(breaker.daily_usd_cap, 2.00)
    breaker.calls_per_hour_cap = max(breaker.calls_per_hour_cap, 1000)
    cases = build_cases()
    # variants inherit their origin's task contract, so the checker can grade them too
    base_tasks = checker.load_tasks()
    tasks = {c["session"].id: base_tasks[c["expected"]["origin"]] for c in cases if c["expected"]["origin"] in base_tasks}
    checker.load_tasks = lambda: tasks
    results = []
    for i, (name, desc, opts) in enumerate(CONFIGS):
        runs = []
        for k in range(REPEATS):
            print(f"running {name} #{k + 1} ...", flush=True)
            runs.append(run_once(name, opts, cases, with_checker=(i == 0)))
            for c in runs[-1]["cases"]:
                if not c["pass"]:
                    print("   MISS", c["name"], {a: b for a, b in c["checks"].items() if not b}, c["state"], c["flags"], c["checker"])
        results.append({"name": name, "desc": desc, "metrics": metrics(runs, i == 0), "runs": runs})
        print("  ", results[-1]["metrics"], flush=True)
    default = results[0]
    misses = {}
    for r in default["runs"]:
        for c in r["cases"]:
            misses.setdefault(c["name"], []).append(c)
    columns = ["state right", "flags right", "secrets right", "injections noticed", "claims dropped",
               "model requests", "tokens", "cost", "seconds", "repeat refresh requests"]
    fmt_exp = lambda e: (e["state"] + (f" + {','.join(e['flags'])}" if e["flags"] else "") + (" + secret" if e["secrets"] else "")
                         + (f" + checker {e['checker']}" if e.get("checker") else ""))
    fmt_got = lambda s: (s["state"] + (f" + {','.join(s['flags'])}" if s["flags"] else "") + (" + secret" if s["secrets"] else "")
                         + (f" + checker {s['checker']}" if s["checker"] else ""))
    out = {
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": config.MODEL,
        "n_cases": len(cases), "repeats": REPEATS, "columns": columns,
        "summary": (f"{len(cases)} cases (8 labeled sample sessions plus {len(cases) - 8} variants), {REPEATS} cold runs "
                    f"per configuration with {config.MODEL}, {datetime.now().strftime('%b %d %Y')}. Ranges are min–max "
                    "over the runs; tokens, cost and seconds are means per cold refresh. \"Repeat refresh\" is the same "
                    "sessions again with nothing changed. The default also ran the done checker on the 6 cases with a "
                    f"task contract: {default['metrics'].get('checker right', 'n/a')} verdicts right."),
        "configs": [{"name": r["name"], "desc": r["desc"], "metrics": r["metrics"]} for r in results],
        "cases": [{"name": name, "expected": fmt_exp(cs[0]["expected"]),
                   "got": " | ".join(fmt_got(c) for c in cs), "pass": all(c["pass"] for c in cs)}
                  for name, cs in misses.items()],
        "details": [{"name": r["name"], "runs": [{k: v for k, v in run.items()} for run in r["runs"]]} for r in results],
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
