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


def test_the_owners_eval_command_is_the_referee():
    from lucidity.agents import planner
    held = "python evals/score.py --split heldout"
    plan = planner.Plan.model_validate({"summary": "s", "nodes": [
        {"id": "t1", "title": "a", "prompt": "p", "budget_usd": 0.5, "done_when": [
            {"kind": "metric", "command": "python evals/score.py --split dev", "metric": "log_loss", "op": "<=", "value": 0.61},
            {"kind": "no_regression", "command": held, "metric": "*.accuracy", "value": 0}]}]})
    clean, problems = planner.validate_plan(plan, 1.0, held)
    # a bar on the split the agents tune on would let work pass on numbers they can see
    assert [c["command"] for c in clean["nodes"][0]["done_when"]] == [held, held]
    assert any("judged with the owner's eval command" in p for p in problems)
    # and "*.accuracy" against flat scores still finds accuracy
    r = contracts._no_regression({"metric": "*.accuracy", "value": 0}, {"accuracy": 0.66}, {"accuracy": 0.6525})
    assert r["met"] is True


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


def test_complaint_demo_races_agents_and_merges_the_best(orch):
    # its recorded model answers are seeded into the repo, so scoring needs no key
    run = wait(runs.create("", worker="demo", demo_name="complaints", demo_speed=0, auto_run=True))
    assert run.d["demo"] == "complaints" and run.d["state"] == "done", run.d["reason"]
    assert run.d["scores"][0]["metrics"]["accuracy"] == pytest.approx(0.7986, abs=1e-4)
    t2, t3 = node(run, "t2"), node(run, "t3")
    # two agents per prompt strategy, each in its own worktree, each checked on held-out scores
    assert [a["id"] for a in t2["agents"]] == ["t2a", "t2b"] and len({a["branch"] for a in t2["agents"]}) == 2
    a, b = t2["agents"]
    assert a["picked"] and [c["verdict"] for c in a["checks"]][:1] == ["pass"]
    assert b["state"] == "failed" and [c["verdict"] for c in b["checks"]] == ["fail", "fail"]
    # one agent got within a rounding of the bar; the check reads 0.847, not 0.85
    assert t3["state"] == "skipped" and "0.847" in t3["agents"][0]["checks"][-1]["reasons"][0]
    # t1 merged while t2a worked, so t2a was checked again on top before it merged
    assert any(e["kind"] == "recheck" and e["node"] == "t2" for e in run.d["events"])
    final = run.d["scores"][-1]["metrics"]
    assert final["accuracy"] == pytest.approx(0.875, abs=1e-3) and run.d["spend_by"].get("eval", 0) == 0


def test_a_score_just_under_its_bar_shows_enough_digits():
    c = {"kind": "metric", "command": "python evals/score.py", "metric": "accuracy", "op": ">=", "value": 0.85}
    r = contracts._metric(c, {"accuracy": 0.8472}, {"accuracy": 0.7847})
    assert r["met"] is False and r["evidence"] == "0.7847 → 0.8472, needs ≥ 0.85"
    assert contracts._metric(c, {"accuracy": 0.8542}, {})["evidence"] == "now 0.8542"


def wait_for_owner(run, timeout=30):
    end = time.time() + timeout
    while time.time() < end and not run.d.get("awaiting_owner"):
        time.sleep(0.05)
    assert run.d["state"] == "plan_ready" and run.d["awaiting_owner"], run.d["state"]
    return run


def test_nba_demo_waits_for_the_owners_picks_and_runs_one_agent_per_pick(orch):
    # the default demo: auto_run still stops at the plan, because only the person picks the model families
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    assert run.d["demo"] == "nba"
    q = run.d["questions"][0]
    assert q["drives"] == "models" and q["multi"] and len(q["options"]) == 6
    run.act("approve", answers={q["id"]: ["SVM", "kNN", "not an option"]})
    wait(run)
    agents = node(run, "models")["agents"]
    assert [a["id"] for a in agents] == ["modelsa", "modelsb"]   # letters follow the option, not the pick order
    assert run.d["questions"][0]["answer"] == ["SVM", "kNN"]
    a, b = agents
    assert "Stick to kNN" in a["prompt"] and any(c["kind"] == "rubric" and "kNN" in c["text"] for c in a["done_when"])
    assert b["picked"] and a["state"] == "failed" and len(a["checks"]) == 4
    assert any("0.6209" in (c.get("evidence") or "") for c in a["checks"][-1]["conditions"])
    # the checker model's ruling, replayed: the SVM really is the model that predicts
    judged = [c for c in b["checks"][-1]["conditions"] if c["kind"] == "rubric"]
    assert judged and judged[0]["met"] is True and "SVC" in judged[0]["evidence"]
    assert run.d["state"] == "done" and run.d["scores"][-1]["metrics"]["log_loss"] == pytest.approx(0.6052, abs=1e-4)


def test_beating_538_by_less_than_the_margin_is_not_a_pass(orch):
    # ridge scores 0.6074, ahead of FiveThirtyEight's 0.608 by a hair; the goal asks for 0.2% (0.6068)
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    q = run.d["questions"][0]
    run.act("approve", answers={q["id"]: ["Ridge logistic regression"]})
    wait(run)
    n = node(run, "models")
    a = n["agents"][0]
    assert a["state"] == "failed" and not n.get("picked") and run.d["state"] == "needs_you"
    bars = [c for ch in a["checks"] for c in ch["conditions"] if c["kind"] == "metric"]
    assert not any(c["met"] for c in bars) and any("0.6074, needs" in c["evidence"] for c in bars)


def test_no_answer_tries_every_approach_and_recommends_one(orch):
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    run.act("approve")
    t0 = time.time()
    wait(run, timeout=600)
    print("six-agent replay took", round(time.time() - t0), "s")
    labels = [o["label"] for o in run.d["questions"][0]["options"]]
    assert run.d["questions"][0]["answer"] == labels
    n = node(run, "models")
    assert [a["id"] for a in n["agents"]] == [f"models{x}" for x in "abcdef"]
    assert [a["label"] for a in n["agents"]] == labels
    c = n["comparison"]
    assert [r["label"] for r in c["rows"]] == ["SVM", "Ridge logistic regression", "Random forest",
                                               "Lasso logistic regression", "Boosted trees", "kNN"]
    assert [r["passed"] for r in c["rows"]] == [True, False, False, False, False, False]   # only the SVM beats 538 by 0.2%
    assert c["rows"][0]["value"] == pytest.approx(0.6052, abs=1e-4)
    assert c["text"].startswith("Recommended: SVM.") and "Runner-up: Ridge logistic regression" in c["text"]
    assert c["rows"][4]["why"] == "changed the scorer" and c["rows"][5]["why"].startswith("missed the bar")
    assert any(e["kind"] == "recommend" for e in run.d["events"])
    assert run.d["state"] == "done" and n["picked"] == "modelsb"
    assert any(e["kind"] == "you" and e["text"].startswith("you chose: ") for e in run.d["events"])


def test_the_stock_demo_recommends_nothing_when_nothing_beats_a_coin_flip(orch):
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True, demo_name="stocks"))
    run.act("approve")
    wait(run, timeout=900)
    n = node(run, "models")
    c = n["comparison"]
    assert [r["label"] for r in c["rows"]][0] == "Random forest" and len(c["rows"]) == 6
    assert not any(r["passed"] for r in c["rows"])
    assert c["rows"][0]["value"] == pytest.approx(0.6929, abs=1e-4)
    assert c["text"] == "No approach cleared the bar. Closest: Random forest at 0.6929."
    assert run.d["state"] == "needs_you" and not n.get("picked")   # nothing merges; the owner decides
    assert node(run, "integration")["state"] == "queued"


def test_the_credit_demo_recommends_the_random_forest_from_six_families(orch):
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True, demo_name="credit"))
    q = run.d["questions"][0]
    run.act("approve", answers={q["id"]: [o["label"] for o in q["options"]]})
    wait(run, timeout=900)
    n = node(run, "models")
    c = n["comparison"]
    assert [r["label"] for r in c["rows"]][:2] == ["Random forest", "Boosted trees"] and len(c["rows"]) == 6
    assert all(r["passed"] for r in c["rows"])   # every family beats plain regression's 0.4666
    assert c["rows"][0]["value"] == pytest.approx(0.4227, abs=1e-4)
    assert c["text"].startswith("Recommended: Random forest.")
    assert run.d["state"] == "done" and n["picked"] == "modelse"
    assert c["importance"]["label"] == "Random forest" and c["importance"]["rows"][0][0] == "status_sep"


def test_the_fed_demo_picks_the_random_forest_and_explains_it(orch):
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True, demo_name="fed"))
    q = run.d["questions"][0]
    run.act("approve", answers={q["id"]: [o["label"] for o in q["options"]]})
    wait(run, timeout=900)
    n = node(run, "race")
    c = n["comparison"]
    assert [r["label"] for r in c["rows"]][:2] == ["Random forest", "kNN"] and len(c["rows"]) == 6
    assert [r["passed"] for r in c["rows"]] == [True, True, False, False, False, False]
    assert c["rows"][0]["value"] == pytest.approx(0.2723, abs=1e-4)
    assert c["importance"]["rows"][0][0] == "yield_3m_gap"     # the market's read of the next move leads
    assert run.d["state"] == "done" and n["picked"] == "racee"


def test_an_agent_that_edits_the_scorer_fails_unscored(orch, monkeypatch, tmp_path):
    from lucidity.orch import demo
    real = demo.Scenario.step

    def step(self, node_id, round_no):
        s = real(self, node_id, round_no)
        if s and node_id == "modelsd":   # the ridge agent also rewrites the scorer to print a perfect score
            rigged = tmp_path / "rigged"
            if not rigged.exists():
                import shutil
                shutil.copytree(s["files_dir"], rigged)
                (rigged / "evals").mkdir(exist_ok=True)
                (rigged / "evals" / "score.py").write_text(
                    """print('{"metrics": {"log_loss": 0.01, "accuracy": 0.99}}')
""", encoding="utf-8")
            s = {**s, "files_dir": rigged}
        return s
    monkeypatch.setattr(demo.Scenario, "step", step)
    run = wait_for_owner(runs.create("", worker="demo", demo_speed=0, auto_run=True))
    q = run.d["questions"][0]
    run.act("approve", answers={q["id"]: ["Ridge logistic regression", "SVM"]})
    wait(run)
    b, d = node(run, "models")["agents"]
    assert d["state"] == "failed" and d["checks"][0]["tampered"] == ["evals/score.py"]
    assert b["picked"] and run.d["scores"][-1]["metrics"]["log_loss"] == pytest.approx(0.6052, abs=1e-4)


def test_known_scores_only_cover_identical_code(tmp_path, monkeypatch):
    import shutil
    repo = tmp_path / "hoopkit"
    shutil.copytree(config.SAMPLE_DIR / "demos" / "nba" / "repo", repo)
    cmd = "python evals/score.py --split heldout"
    key = contracts._code_key(cmd, repo)
    monkeypatch.setattr(contracts, "KNOWN_SCORES", {key: {"metrics": {"log_loss": 0.5}}})
    assert contracts.score(cmd, repo)["metrics"]["log_loss"] == 0.5   # same code, same score: no rerun
    assert contracts._code_key("python evals/score.py --split dev", repo) != key
    (repo / "hoopkit" / "model.py").write_text((repo / "hoopkit" / "model.py").read_text() + "\n# tuned\n")
    assert contracts._code_key(cmd, repo) != key   # any edit misses, and is scored for real
    assert contracts.score(cmd, repo)["metrics"]["log_loss"] == pytest.approx(0.6234, abs=1e-4)


def test_an_agent_cannot_score_the_held_out_split(tmp_path):
    import os
    import subprocess
    import sys
    repo = config.SAMPLE_DIR / "demos" / "nba" / "repo"
    env = {**os.environ, "LUCIDITY_ROLE": "agent"}
    r = subprocess.run([sys.executable, "evals/score.py", "--split", "heldout"], cwd=repo, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 2 and "only shown to the referee" in r.stdout
    r = subprocess.run([sys.executable, "evals/score.py", "--split", "dev"], cwd=repo, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["split"] == "dev"


def test_a_split_prefixed_metric_reads_flat_scores():
    # A planner may write "held_out.rmse" for an eval that prints {"rmse": ...} for the split it scored.
    c = {"kind": "metric", "command": "python evals/score.py", "metric": "held_out.rmse", "op": "<=", "value": 69.154}
    r = contracts._metric(c, {"rmse": 55.1, "r2": 0.45}, {"rmse": 76.84, "r2": 0.01})
    assert r["met"] is True and r["evidence"] == "76.84 → 55.10"
    assert contracts._no_regression({"metric": "*.r2", "value": 0}, {"r2": 0.45}, {"r2": 0.01})["met"] is True
    assert contracts.metric_key({"currency.f1": 0.9, "f1": 0.5}, "currency.f1") == "currency.f1"
    assert contracts.metric_key({"f1": 0.5}, "currency.f1") == "currency.f1"   # not a split name: no guessing


def test_a_plan_starts_once(orch):
    import threading
    run = wait(runs.create("", worker="demo", demo_name="shop", demo_speed=0))
    errors = []

    def click():
        try:
            run.approve()
        except runs.RunError as e:
            errors.append(str(e))
    clicks = [threading.Thread(target=click) for _ in range(2)]
    for t in clicks:
        t.start()
    for t in clicks:
        t.join()
    assert len(errors) == 1   # auto-run and a click, or a double click, start the run once
    assert sum(e["text"].startswith("plan approved") for e in run.d["events"]) == 1
