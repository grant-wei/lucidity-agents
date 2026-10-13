"""The orchestrator loop: goal -> plan -> worktrees -> worker -> check -> merge, on the bundled demo
repo with real git and real test runs. The demo worker's edits are scripted (speed 0, so no waiting);
everything after them is the real code path."""
import json
import time

import pytest

from lucidity import config
from lucidity.orch import contracts, gate, runs, worktrees

pytestmark = pytest.mark.skipif(not worktrees.available(), reason="git not installed")
SETTLED = ("plan_ready", "done", "needs_you", "failed", "stopped")


@pytest.fixture
def orch(sandbox, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_KEY_PRESENT", False, raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(runs, "TICK_S", 0.02)
    runs._registry.clear()
    yield sandbox
    for r in list(runs._registry.values()):
        r.cancel.set()
        r.d["state"] = "stopped"
    end = time.time() + 15        # let worker threads notice before the sandbox goes away
    while time.time() < end and any(t.name.startswith(tuple(runs._registry)) or t.name.startswith("run-")
                                    for t in __import__("threading").enumerate()):
        time.sleep(0.05)
    runs._registry.clear()


def wait(run, states=SETTLED, timeout=90):
    end = time.time() + timeout
    if run.d["auto_run"]:
        states = tuple(s for s in states if s != "plan_ready")   # passes through it on the way to running
    while time.time() < end:
        if run.d["state"] in states and not any(n["state"] == "running" for n in run.d["nodes"]):
            return run
        time.sleep(0.05)
    raise AssertionError(f"run stuck in {run.d['state']}: {[(n['id'], n['state']) for n in run.d['nodes']]}")


def node(run, nid):
    return run.node(nid)


def test_plan_waits_for_approval(orch):
    run = wait(runs.create("", worker="demo", demo_speed=0))
    assert run.d["state"] == "plan_ready"
    assert [n["id"] for n in run.d["nodes"]] == ["t1", "t2", "t3", "t4", "t5", "t6"]
    assert all(n["state"] == "queued" for n in run.d["nodes"]) and run.d["integration"] is None
    assert run.d["spent_usd"] == pytest.approx(0.0042)      # the (scripted) planner call
    saved = json.loads((config.STATE_DIR / "runs" / f"{run.id}.json").read_text(encoding="utf-8"))
    assert saved["state"] == "plan_ready"


def test_demo_run_end_to_end(orch):
    run = wait(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    # t4 spends its whole budget on a wrong first round and waits for you; everything it doesn't block finishes
    assert run.d["state"] == "needs_you"
    t3, t4 = node(run, "t3"), node(run, "t4")
    assert [c["verdict"] for c in t3["checks"]] == ["fail", "pass"] and t3["state"] == "done"
    assert "test_discount_follows_later_cart_changes" in t3["checks"][0]["reasons"][0] or t3["checks"][0]["reasons"]
    assert t4["state"] == "needs_you" and t4["needs_kind"] == "budget"
    assert node(run, "t6")["state"] == "queued"
    assert run.view()["needs"][0]["actions"] == ["add_budget", "skip"]

    run.act("add_budget", node="t4", amount=0.15)
    wait(run, ("done", "needs_you", "failed", "stopped"))
    assert run.d["state"] == "done", run.d["reason"]
    assert all(n["state"] == "done" for n in run.d["nodes"])
    assert [c["verdict"] for c in node(run, "t4")["checks"]] == ["fail", "pass"]
    assert run.d["spent_usd"] == pytest.approx(1.0842, abs=1e-4)

    # the work is merged into the run's branch; the repo's own branch is untouched
    repo, integ = run.d["repo"], run.d["integration"]
    assert worktrees.head(repo) == run.d["base_commit"]
    log = worktrees.git(integ["path"], "log", "--oneline", check=True).stdout
    assert log.count("checks passed") == 6
    assert set(run.d["files_changed"]) >= {"shop/pricing/codes.py", "shop/cart/cart.py", "shop/api/routes.py", "README.md"}
    whole = contracts.evaluate([{"kind": "test", "command": "python -m pytest -q", "path": "", "text": ""}], integ["path"])
    assert whole[0]["met"] is True, whole[0]["evidence"]
    # charts have something to draw
    assert len(run.d["samples"]) > 3 and run.d["samples"][-1]["done"] == 6
    assert all(s["end"] is not None for n in run.d["nodes"] for s in n["spans"])


def test_run_budget_cap_stops_new_tasks(orch):
    run = wait(runs.create("", worker="demo", demo_speed=0, auto_run=True, budget_usd=0.3))
    assert run.d["state"] == "needs_you" and run.d["needs_kind"] == "run_budget"
    assert run.view()["needs"][0]["actions"] == ["raise_budget", "stop"]
    assert run.d["spent_usd"] >= 0.3 and any(n["state"] == "queued" for n in run.d["nodes"])
    with pytest.raises(runs.RunError):
        run.act("raise_budget", amount=config.MAX_RUN_USD)
    run.act("raise_budget", amount=1.0)
    assert run.d["budget_usd"] == pytest.approx(1.3)
    wait(run, ("needs_you", "done"))
    # the planner scaled each task's share down to fit $0.30, so now the per-task caps stop them
    assert node(run, "t3")["budget_usd"] < 0.40
    assert node(run, "t3")["needs_kind"] == "budget" and run.d["spent_usd"] > 0.3


def test_skip_and_stop(orch):
    run = wait(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    run.act("skip", node="t4")
    assert node(run, "t4")["state"] == "skipped"
    wait(run, ("done", "needs_you", "stopped"))
    assert node(run, "t6")["round"] >= 1            # its dependency was skipped, so it ran
    with pytest.raises(runs.RunError):
        run.act("skip", node="t1")                   # done work can't be skipped
    run.act("stop")
    assert run.d["state"] == "stopped"
    with pytest.raises(runs.RunError):
        run.act("dance")


def test_bad_requests(orch, tmp_path):
    with pytest.raises(runs.RunError, match="budget"):
        runs.create("", worker="demo", budget_usd=config.MAX_RUN_USD + 1)
    with pytest.raises(runs.RunError, match="worker"):
        runs.create("do a thing to the repo", worker="nope", repo=tmp_path)
    with pytest.raises(runs.RunError, match="OPENAI_API_KEY|needs"):
        runs.create("do a thing to the repo", worker="builtin", repo=tmp_path)


def test_restart_marks_running_runs_stopped(orch):
    run = wait(runs.create("", worker="demo", demo_speed=0))
    data = dict(run.d, state="running")
    data["nodes"] = [dict(n, state="running") if n["id"] == "t1" else n for n in run.d["nodes"]]
    p = config.STATE_DIR / "runs" / f"{run.id}.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    loaded = runs._load(p)
    assert loaded.d["state"] == "stopped" and loaded.node("t1")["state"] == "stopped"


def test_gate_rules(orch):
    n = {"id": "t", "title": "x", "prompt": "", "done_when": [{"kind": "test", "command": "python -m pytest", "path": "", "text": ""}]}
    failed = [{"kind": "test", "label": "tests pass", "met": False, "evidence": "1 failed"}]
    assert gate.grade(n, failed, "done!", "diff")["verdict"] == "fail"
    passed = [{"kind": "test", "label": "tests pass", "met": True, "evidence": "3 passed"}]
    v = gate.grade(n, passed, "done", "diff")
    assert v["verdict"] == "pass" and v["by"] == "program" and v["usd"] == 0
    rub = dict(n, done_when=n["done_when"] + [{"kind": "rubric", "text": "the code is readable", "path": "", "command": ""}])
    assert gate.grade(rub, passed + [{"kind": "rubric", "label": "r", "met": None, "evidence": ""}], "done", "diff")["verdict"] == "needs_you"


def test_contracts_and_merge_conflict(orch, tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    worktrees.init_repo(repo, "init")
    base = worktrees.head(repo)
    got = contracts.evaluate([{"kind": "file_contains", "path": "a.txt", "text": "one", "command": ""},
                              {"kind": "file_contains", "path": "../outside", "text": "x", "command": ""},
                              {"kind": "test", "command": "rm -rf /", "path": "", "text": ""}], repo)
    assert [g["met"] for g in got] == [True, False, False]
    a, b = tmp_path / "wa", tmp_path / "wb"
    worktrees.add(repo, a, "ta", base)
    worktrees.add(repo, b, "tb", base)
    (a / "a.txt").write_text("two\n", encoding="utf-8")
    (b / "a.txt").write_text("three\n", encoding="utf-8")
    worktrees.commit_all(a, "a")
    worktrees.commit_all(b, "b")
    assert worktrees.changed_files(a, base) == ["a.txt"]
    first = worktrees.merge(repo, "ta", "merge a")
    second = worktrees.merge(repo, "tb", "merge b")
    assert first["ok"] and not second["ok"] and second["conflicts"] == ["a.txt"]
    assert (repo / "a.txt").read_text(encoding="utf-8") == "two\n"     # the failed merge was aborted
