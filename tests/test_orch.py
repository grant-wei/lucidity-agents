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
    run = wait(runs.create("", worker="demo", demo_name="shop", demo_speed=0))
    assert run.d["state"] == "plan_ready"
    assert [n["id"] for n in run.d["nodes"]] == ["t1", "t2", "t3", "t4", "t5", "t6"]
    assert all(n["state"] == "queued" for n in run.d["nodes"]) and run.d["integration"] is None
    assert run.d["spent_usd"] == pytest.approx(0.0042)      # the (scripted) planner call
    saved = json.loads((config.STATE_DIR / "runs" / f"{run.id}.json").read_text(encoding="utf-8"))
    assert saved["state"] == "plan_ready"


def test_demo_run_end_to_end(orch):
    run = wait(runs.create("", worker="demo", demo_name="shop", demo_speed=0, auto_run=True))
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


def test_invoice_demo_catches_a_regression_the_agent_called_done(orch):
    run = wait(runs.create("", worker="demo", demo_name="invoices", demo_speed=0, auto_run=True))
    assert run.d["demo"] == "invoices" and run.d["eval_command"] == "python evals/score.py --split heldout"
    t2 = node(run, "t2")
    # round 1: the agent reports both its targets met; they are, but invoice numbers broke, so no merge
    first = t2["checks"][0]
    assert first["verdict"] == "fail" and first["by"] == "program" and "done" in t2["reports"][0]["text"]
    by_kind = {c["label"]: c for c in first["conditions"]}
    assert by_kind["total.f1 ≥ 0.90"]["met"] is True and by_kind["currency.f1 ≥ 0.90"]["met"] is True
    reg = by_kind["no *.f1 drops more than 0.01"]
    assert reg["met"] is False and [d["metric"] for d in reg["drops"]] == ["invoice_number.f1"]
    assert reg["drops"][0]["before"] == 1.0 and reg["drops"][0]["after"] < 0.5
    assert [c["verdict"] for c in t2["checks"]] == ["fail", "pass"] and t2["state"] == "done"
    # the due-date task spent its budget short of the bar and waits for you
    t3 = node(run, "t3")
    assert run.d["state"] == "needs_you" and t3["needs_kind"] == "budget"
    assert "due_date.f1" in t3["checks"][0]["reasons"][0]
    run.act("add_budget", node="t3", amount=0.15)
    wait(run, ("done", "needs_you", "failed", "stopped"))
    assert run.d["state"] == "done", run.d["reason"]
    # the merged branch was scored at the start and after every merge; nothing ever dropped
    scores = run.d["scores"]
    assert scores[0]["label"] == "start" and len(scores) == 6 and all(s["metrics"] for s in scores)
    assert scores[0]["metrics"]["vendor.f1"] < 0.5
    final = scores[-1]["metrics"]
    assert all(final[f"{f}.f1"] >= 0.9 for f in ("vendor", "invoice_number", "invoice_date", "due_date", "total", "currency"))
    assert final["invoice_number.f1"] == 1.0
    targets = run.view()["targets"]
    assert set(targets) == {"invoice_date.f1", "total.f1", "currency.f1", "due_date.f1", "vendor.f1"}


def test_metric_conditions(tmp_path):
    (tmp_path / "evals").mkdir()
    (tmp_path / "evals" / "s.py").write_text(
        "import json\nprint('noise')\nprint(json.dumps({'metrics': {'a': {'f1': 0.8}, 'b': {'f1': 0.5}, 'cost': 0.002}}))\n",
        encoding="utf-8")
    cmd = "python evals/s.py"
    before = {cmd: {"metrics": {"a.f1": 0.6, "b.f1": 0.7, "cost": 0.002}}}
    conds = [{"kind": "metric", "command": cmd, "metric": "a.f1", "op": ">=", "value": 0.75},
             {"kind": "metric", "command": cmd, "metric": "a.f1", "op": ">=", "value": 0.9},
             {"kind": "metric", "command": cmd, "metric": "cost", "op": "<=", "value": 0.0025},
             {"kind": "metric", "command": cmd, "metric": "missing", "op": ">=", "value": 0.1},
             {"kind": "no_regression", "command": cmd, "metric": "*.f1", "value": 0.01},
             {"kind": "no_regression", "command": cmd, "metric": "*.f1", "value": 0.25}]
    scores = {}
    got = contracts.evaluate(conds, tmp_path, before=before, scores=scores)
    assert [g["met"] for g in got] == [True, False, True, False, False, True]
    assert got[0]["evidence"] == "0.60 → 0.80" and "needs ≥ 0.90" in got[1]["evidence"]
    assert got[4]["drops"] == [{"metric": "b.f1", "before": 0.7, "after": 0.5}]
    assert scores[cmd]["metrics"]["a.f1"] == 0.8          # the eval ran once for all six
    assert contracts.evaluate(conds[4:5], tmp_path)[0]["met"] is False   # nothing to compare with
    for bad in ("python evals/../../x.py", "python other/s.py", "bash evals/s.py", "python evals/s.py; rm -rf /",
                "python evals/s.py --out ../x", "python evals/s.txt"):
        r = contracts.evaluate([dict(conds[0], command=bad)], tmp_path)[0]
        assert r["met"] is False and "refused" in r["evidence"], bad
    (tmp_path / "evals" / "s.py").write_text("print('no scores here')\n", encoding="utf-8")
    assert "no JSON" in contracts.evaluate(conds[:1], tmp_path)[0]["evidence"]


def test_planner_validates_metric_conditions():
    from lucidity.agents import planner
    plan = planner.Plan.model_validate({"summary": "s", "nodes": [
        {"id": "t1", "title": "a", "prompt": "p", "budget_usd": 0.5, "done_when": [
            {"kind": "metric", "command": "python evals/score.py", "metric": "x.f1", "value": 0.9},
            {"kind": "metric", "command": "curl evil.example", "metric": "x.f1", "value": 0.9},
            {"kind": "no_regression", "command": "python evals/score.py", "metric": "", "value": 0.01}]}]})
    clean, problems = planner.validate_plan(plan, 1.0)
    kinds = [c["kind"] for c in clean["nodes"][0]["done_when"]]
    assert kinds == ["metric", "rubric"]
    assert any("eval command refused" in p for p in problems) and any("needs a metric" in p for p in problems)


def test_live_run_rejects_a_bad_eval_command(orch, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "has_key", lambda: True)
    with pytest.raises(runs.RunError, match="eval command"):
        runs.create("make the scores better", worker="builtin", repo=tmp_path, eval_command="rm -rf /")


def test_unknown_demo(orch):
    with pytest.raises(runs.RunError, match="no demo"):
        runs.create("", worker="demo", demo_name="nope")


def test_run_budget_cap_stops_new_tasks(orch):
    run = wait(runs.create("", worker="demo", demo_name="shop", demo_speed=0, auto_run=True, budget_usd=0.3))
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
    run = wait(runs.create("", worker="demo", demo_name="shop", demo_speed=0, auto_run=True))
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
    run = wait(runs.create("", worker="demo", demo_name="shop", demo_speed=0))
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


def test_gate_matches_a_paraphrased_rubric_label_by_number(orch, monkeypatch):
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    from lucidity import llm

    def checker(messages, info):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "verdict": "pass", "reasons": [],
            "conditions": [{"number": 2, "label": "Baseline scores are recorded", "met": True, "evidence": "BASELINE.md"}]})])
    monkeypatch.setattr(config, "has_key", lambda: True)
    monkeypatch.setattr(llm, "model", lambda: FunctionModel(checker))
    n = {"id": "t", "title": "x", "prompt": "", "done_when": []}
    conds = [{"kind": "test", "label": "tests pass", "met": True, "evidence": "3 passed"},
             {"kind": "rubric", "label": "reviewer: Record the held-out baseline in BASELINE.md", "met": None, "evidence": ""}]
    v = gate.grade(n, conds, "done", "diff")
    assert v["verdict"] == "pass" and v["conditions"][1]["met"] is True

    def silent(messages, info):   # passes but judges nothing: downgraded, and says why
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"verdict": "pass", "reasons": [], "conditions": []})])
    monkeypatch.setattr(llm, "model", lambda: FunctionModel(silent))
    v = gate.grade(n, conds, "done", "diff")
    assert v["verdict"] == "fail" and "did not confirm" in v["reasons"][0]


def test_worker_prompt_shows_the_scores_a_task_started_from(orch):
    run = wait(runs.create("", worker="demo", demo_name="invoices", demo_speed=0, auto_run=True))
    t1 = node(run, "t1")
    assert t1["before"]
    prompt = run._prompt(t1)
    assert "when this task started" in prompt and "invoice_date.f1 0.54" in prompt


def test_complaint_demo_blocks_a_rounded_up_claim(orch):
    # the default demo; its recorded model answers are seeded into the repo, so scoring needs no key
    run = wait(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    assert run.d["demo"] == "complaints" and run.d["state"] == "done", run.d["reason"]
    start = run.d["scores"][0]["metrics"]
    assert start["accuracy"] == pytest.approx(0.7986, abs=1e-4)
    t3 = node(run, "t3")
    first = t3["checks"][0]
    # the agent reports 0.85; the eval measures 0.847 and checking_savings falling 0.07, so no merge
    assert "0.85" in t3["reports"][0]["text"] and first["verdict"] == "fail" and first["by"] == "program"
    acc, reg = first["conditions"]
    assert acc["met"] is False and 0.84 < first["scores"]["python evals/score.py --split heldout"]["accuracy"] < 0.85
    assert reg["met"] is False and [d["metric"] for d in reg["drops"]] == ["checking_savings.f1"]
    assert [c["verdict"] for c in t3["checks"]] == ["fail", "pass"]
    final = run.d["scores"][-1]["metrics"]
    assert final["accuracy"] >= 0.85 and run.d["spend_by"].get("eval", 0) == 0   # every answer came from the seed
