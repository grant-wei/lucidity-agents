"""Record one real planner -> worker -> checker run into sample_data/replays/, so sample mode can
play it back without spawning anything. Everything in the file comes from this run.

    python scripts/record_replay.py          # needs flask (requirements-dev.txt) and an API key
"""
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lucidity import config  # noqa: E402
from lucidity.agents import planner, worker  # noqa: E402
from lucidity.agents.checker import run_allowlisted_command  # noqa: E402
from lucidity.llm import run_agent  # noqa: E402

GOAL = "add a dark mode toggle to a small flask app"
FIXTURE = ROOT / "sample_data" / "replay_fixture" / "flask-notes"
OUT = ROOT / "sample_data" / "replays" / "dark_mode_toggle.json"
TOTAL_BUDGET = 0.50


def check_conditions(conds, root):
    results = []
    for c in conds:
        if c["kind"] == "test":
            r = run_allowlisted_command(c["command"], root)
            ok = r.get("exit_code") == 0
            results.append({**c, "met": ok, "evidence": (r.get("output") or r.get("reason") or "")[-300:]})
        elif c["kind"] == "file_contains":
            p = root / c["path"]
            ok = p.is_file() and c["text"] in p.read_text(encoding="utf-8", errors="replace")
            results.append({**c, "met": ok, "evidence": "found" if ok else "not found"})
        else:
            results.append({**c, "met": None, "evidence": "rubric: needs a person or the checker agent"})
    return results


def main():
    t0 = time.time()
    events = []

    def ev(kind, **data):
        events.append({"t": round(time.time() - t0, 2), "kind": kind, **data})

    work = Path(tempfile.mkdtemp(prefix="lucidity-replay-")) / "flask-notes"
    shutil.copytree(FIXTURE, work, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    files = sorted(str(p.relative_to(work)).replace("\\", "/") for p in work.rglob("*") if p.is_file())
    desc = "Files: " + ", ".join(files) + "\nREADME: " + (work / "README.md").read_text(encoding="utf-8")
    ev("goal", text=GOAL, budget_usd=TOTAL_BUDGET)
    plan, row, _ = planner.plan(GOAL, desc, TOTAL_BUDGET)
    ev("plan", plan=plan, usd=row["usd"], tokens=row["input_tokens"] + row["output_tokens"])
    spent = row["usd"]
    status = {}
    for nid in plan["order"]:
        node = next(n for n in plan["nodes"] if n["id"] == nid)
        if any(status.get(d) != "done" for d in node["deps"]):
            status[nid] = "skipped"
            ev("node_skipped", node=nid, reason="a dependency did not finish")
            continue
        ev("node_start", node=nid, title=node["title"], budget_usd=node["budget_usd"], max_rounds=node["max_rounds"])
        # a condition that already passes before any work proves nothing about this node
        pre = check_conditions(node["done_when"], work)
        weak = [c for c in pre if c["met"] is True]
        if weak:
            ev("weak_contract", node=nid, conditions=[c.get("command") or c.get("path") for c in weak],
               reason="already true before the worker started, so passing it proves nothing")
        node_spent, feedback = 0.0, ""
        for rnd in range(1, node["max_rounds"] + 1):
            conds_text = "\n".join(f"- {c['kind']}: {c.get('command') or ''} {c.get('path') or ''} {c.get('text') or ''}".strip()
                                   for c in node["done_when"])
            prompt = f"Task: {node['prompt']}\nDone when:\n{conds_text}\n{feedback}"
            deps = worker.Deps(root=work)
            reply, wrow = run_agent(worker.agent, prompt, name="worker", deps=deps, request_limit=25)
            node_spent += wrow["usd"]
            spent += wrow["usd"]
            ev("worker_round", node=nid, round=rnd, tools=deps.log, reply=reply, usd=wrow["usd"],
               tokens=wrow["input_tokens"] + wrow["output_tokens"])
            checks = check_conditions(node["done_when"], work)
            ok = all(c["met"] is not False for c in checks)
            ev("check", node=nid, round=rnd, results=checks, passed=ok)
            if ok:
                status[nid] = "done"
                break
            if node_spent >= node["budget_usd"]:
                status[nid] = "stopped"
                ev("node_stopped", node=nid, reason=f"over its ${node['budget_usd']:.2f} budget")
                break
            feedback = "Your last attempt failed these checks:\n" + "\n".join(
                f"- {c['kind']} {c.get('command') or c.get('path')}: {c['evidence'][-200:]}" for c in checks if c["met"] is False)
        else:
            status[nid] = "needs_owner"
            ev("node_needs_owner", node=nid, reason=f"still failing after {node['max_rounds']} rounds")
        if status[nid] == "done":
            ev("node_done", node=nid, usd=round(node_spent, 6))
    final = run_allowlisted_command("python -m pytest -q", work)
    ev("final_tests", exit_code=final.get("exit_code"), output=(final.get("output") or "")[-400:])
    changed = {}
    for p in work.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts:
            rel = str(p.relative_to(work)).replace("\\", "/")
            orig = FIXTURE / rel
            new = p.read_text(encoding="utf-8", errors="replace")
            if not orig.exists() or orig.read_text(encoding="utf-8", errors="replace") != new:
                changed[rel] = new[:4000]
    record = {
        "replay": True,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": config.MODEL, "goal": GOAL, "budget_usd": TOTAL_BUDGET,
        "spent_usd": round(spent, 6), "seconds": round(time.time() - t0, 1),
        "status": status, "events": events, "changed_files": changed,
        "note": "Recorded by scripts/record_replay.py from a real run; sample mode plays it back.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1), encoding="utf-8")
    shutil.rmtree(work.parent, ignore_errors=True)
    return record


if __name__ == "__main__":
    r = main()
    print(f"goal: {r['goal']}  spent ${r['spent_usd']:.4f} of ${r['budget_usd']:.2f}  in {r['seconds']}s")
    plan = next(e for e in r["events"] if e["kind"] == "plan")["plan"]
    print("\nplan:", plan["summary"])
    for n in plan["nodes"]:
        print(f"  {n['id']} {n['title']}  deps={n['deps']}  ${n['budget_usd']}  rounds<={n['max_rounds']}")
        for c in n["done_when"]:
            print(f"      done when {c['kind']}: {c.get('command') or c.get('path')} {c.get('text') or ''}".rstrip())
    if plan["problems"]:
        print("  validator:", plan["problems"])
    print("\ntimeline:")
    for e in r["events"]:
        if e["kind"] == "worker_round":
            print(f"  {e['t']:>6}s worker {e['node']} round {e['round']}: {len(e['tools'])} tool calls, ${e['usd']:.5f}")
        elif e["kind"] == "check":
            print(f"  {e['t']:>6}s check  {e['node']} round {e['round']}: {'pass' if e['passed'] else 'FAIL'} "
                  + ", ".join(f"{c['kind']}={c['met']}" for c in e["results"]))
        elif e["kind"] == "weak_contract":
            print(f"  {e['t']:>6}s WEAK   {e['node']}: {e['conditions']} {e['reason']}")
        elif e["kind"] not in ("plan", "goal"):
            print(f"  {e['t']:>6}s {e['kind']} {e.get('node', '')} {e.get('reason', '') or e.get('exit_code', '')}")
    print("status:", r["status"], "\nchanged files:", list(r["changed_files"]))
