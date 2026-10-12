"""The server, end to end: start it on a free port in sample mode with the fake model, run one
refresh, and hit every route the page uses."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
from lucidity import config
from lucidity.agents import coordinator

from conftest import FakeModel, use_fake


@pytest.fixture
def server(sandbox, monkeypatch):
    use_fake(monkeypatch, FakeModel(state="working"))
    monkeypatch.setattr(config, "has_key", lambda: True)
    monkeypatch.setattr(app, "TRACE_DIR", sandbox / "logs" / "traces")
    monkeypatch.setattr(app, "ACTIONS_LOG", sandbox / "logs" / "actions.jsonl")
    # the checker runs real test suites in the fixtures; it has its own tests, so skip it here
    monkeypatch.setattr(app, "refresh", lambda opts: coordinator.refresh(
        coordinator.Options(mode=opts.mode, run_checker=False)))
    monkeypatch.setattr(app, "_state", {"snapshot": None, "error": None, "refreshing": False, "last_refresh": None})
    monkeypatch.setattr(app, "do_map", lambda: None)   # the map has its own tests; a stray thread would outlive the sandbox
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def get(url, raw=False):
    with urllib.request.urlopen(url, timeout=10) as r:
        body = r.read()
        return r.status, (body if raw else json.loads(body)), r.headers


def post(url, body):
    req = urllib.request.Request(url, data=body if isinstance(body, bytes) else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read())


def status_of(url, body=None):
    try:
        return (post(url, body) if body is not None else get(url))[0]
    except urllib.error.HTTPError as e:
        return e.code


def test_page_loads(server):
    code, html, headers = get(server + "/", raw=True)
    assert code == 200 and headers["Content-Type"].startswith("text/html")
    assert b"<title>" in html and b"/api/snapshot" in html


def test_snapshot_before_and_after_a_refresh(server):
    _, snap, _ = get(server + "/api/snapshot")
    assert "sessions" not in snap and snap["caps"]["daily_usd"] == config.DAILY_USD_CAP
    app.do_refresh()
    _, snap, _ = get(server + "/api/snapshot")
    assert len(snap["sessions"]) == 8 and snap["error"] is None and snap["last_refresh"]
    assert not snap["refreshing"] and snap["model"] == config.MODEL
    waiting = {r["id"] for r in snap["sessions"] if r["state"] == "needs_you"}
    assert "a1f0c2d4-0001-4a00-9000-000000000001" in waiting     # plain code catches it whatever the model says
    flagged = {f["kind"] for r in snap["sessions"] for f in r.get("flags") or []}
    assert flagged == {"runaway", "stalled"}


def test_traces_are_listed_and_readable(server):
    app.do_refresh()
    _, traces, _ = get(server + "/api/traces")
    assert traces and traces[0]["agents"] >= 1
    _, t, _ = get(server + f"/api/trace?id={traces[0]['id']}")
    assert t["id"] == traces[0]["id"] and t["nodes"]


@pytest.mark.parametrize("path", [
    "/api/trace?id=", "/api/trace?id=../../app", "/api/trace?id=..%5C..%5Capp",
    "/static/../app.py", "/static/..%2F.env", "/nope",
])
def test_bad_paths_are_404(server, path):
    assert status_of(server + path) == 404


def test_replay_and_evals_routes(server):
    assert get(server + "/api/replay")[0] == 200
    assert get(server + "/api/evals")[0] == 200


def test_refresh_runs_in_the_background(server):
    assert post(server + "/api/refresh", {})[0] == 202


def test_owner_actions_are_logged_not_executed(server):
    assert post(server + "/api/action", {"session_id": "abc", "action": "stop"}) == (200, {"ok": True})
    rows = [json.loads(x) for x in app.ACTIONS_LOG.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["session_id"] == "abc" and rows[-1]["action"] == "stop"
    assert status_of(server + "/api/action", b"{not json") == 400
    assert status_of(server + "/api/other", {}) == 404


def test_a_failed_refresh_keeps_the_page_up(server, monkeypatch):
    def boom(opts):
        raise RuntimeError("disk full")
    monkeypatch.setattr(app, "refresh", boom)
    app.do_refresh()
    _, snap, _ = get(server + "/api/snapshot")
    assert "disk full" in snap["error"] and not snap["refreshing"]
    assert get(server + "/", raw=True)[0] == 200


def test_missing_key_is_reported(server, monkeypatch):
    monkeypatch.setattr(config, "has_key", lambda: False)
    app.do_refresh()
    _, snap, _ = get(server + "/api/snapshot")
    assert "OPENAI_API_KEY" in snap["error"]
