"""The run routes the page uses: start the demo over HTTP, watch it plan, approve it, read the run,
its repo map and the run list, and get clean 400s for bad requests."""
import time

import pytest

from lucidity import config
from lucidity.orch import runs, worktrees

from test_app import get, post, server, status_of  # noqa: F401  (server is a fixture)
from test_orch import orch  # noqa: F401  (fixture)

pytestmark = pytest.mark.skipif(not worktrees.available(), reason="git not installed")


@pytest.fixture
def api(orch, server, monkeypatch):  # noqa: F811
    monkeypatch.setenv("LUCIDITY_DEMO_SPEED", "0")
    return server


def poll(url, states, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        v = get(url)[1]
        if v["state"] in states and not any(n["state"] == "running" for n in v["nodes"]):
            return v
        time.sleep(0.1)
    raise AssertionError(f"run stuck in {v['state']}")


def test_demo_over_http(api):
    code, runs_list, _ = get(api + "/api/runs")
    assert code == 200 and runs_list["runs"] == []
    assert [d["name"] for d in runs_list["demos"]] == ["invoices", "shop"] and runs_list["max_run_usd"] == config.MAX_RUN_USD
    assert {w["name"] for w in runs_list["workers"]} >= {"demo", "builtin", "claude", "codex"}

    code, made = post(api + "/api/runs", {"worker": "demo", "auto_run": False})   # the invoice demo by default
    assert code == 201 and made["mode"] == "demo" and made["repo_name"] == "invoicekit"
    url = api + "/api/runs/" + made["id"]
    v = poll(url, ("plan_ready",))
    assert len(v["nodes"]) == 5 and v["spend_by"]["planner"] > 0 and v["samples"]
    assert v["targets"]["vendor.f1"]["value"] == 0.9

    code, m, _ = get(url + "/map")
    assert code == 200 and m["modules"] and all("tasks" in x for x in m["modules"])

    assert post(url + "/action", {"action": "approve"})[0] == 200
    v = poll(url, ("needs_you", "done"))
    assert v["state"] == "needs_you" and v["needs"][0]["node"] == "t3"   # the scripted budget overrun
    assert status_of(url + "/action", {"action": "add_budget", "node": "t3"}) == 400   # no amount
    assert post(url + "/action", {"action": "add_budget", "node": "t3", "amount": 0.15})[0] == 200
    v = poll(url, ("done", "needs_you", "failed"))
    assert v["state"] == "done" and v["merged_commit"] and v["files_changed"]
    assert all(n["state"] == "done" for n in v["nodes"])
    final = v["scores"][-1]["metrics"]
    assert all(final[f"{f}.f1"] >= 0.9 for f in ("vendor", "invoice_date", "due_date", "total", "currency"))

    listed = get(api + "/api/runs")[1]["runs"]
    assert listed[0]["id"] == made["id"] and listed[0]["done"] == 5

    assert post(url + "/delete", {})[0] == 200
    assert status_of(url) == 404


def test_bad_run_requests(api, monkeypatch):
    assert status_of(api + "/api/runs", {"worker": "demo", "budget_usd": config.MAX_RUN_USD + 1}) == 400
    assert status_of(api + "/api/runs", {"worker": "nope", "goal": "x"}) == 400
    monkeypatch.setattr(config, "has_key", lambda: False)
    assert status_of(api + "/api/runs", {"worker": "builtin", "goal": "add a thing", "repo": "."}) == 400
    assert status_of(api + "/api/runs/does-not-exist") == 404
    code, made = post(api + "/api/runs", {"worker": "demo"})
    assert status_of(api + f"/api/runs/{made['id']}/action", {"action": "explode"}) == 400
    runs._registry[made["id"]].cancel.set()
