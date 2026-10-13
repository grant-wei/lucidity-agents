"""Lucidity: an orchestrator for coding agents, and one screen to watch them on.

    python app.py            # opens http://127.0.0.1:8765; the demo run needs no key
    LUCIDITY_DATA=local python app.py   # the Sessions tab reads your own Claude Code and Codex sessions

Standard library server, local only. Runs (goal -> plan -> agents -> checks -> merge) live in
lucidity/orch/. A background thread refreshes the Sessions monitor every REFRESH_SECONDS;
unchanged sessions cost nothing, so leaving it open all day is cheap by design."""
import json
import os
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from lucidity import config
from lucidity.agents.coordinator import Options, refresh
from lucidity.agents.mapper import refresh_map
from lucidity.guard import breaker
from lucidity.orch import runmap, runs, workers
from lucidity.trace import TRACE_DIR

STATIC = config.ROOT / "static"
ACTIONS_LOG = config.LOG_DIR / "actions.jsonl"

_lock = threading.Lock()
_state = {"snapshot": None, "error": None, "refreshing": False, "last_refresh": None}
_map_lock = threading.Lock()
_map = {"map": None, "error": None, "building": False}


def seed_sample_cache():
    """No key on a fresh clone: start the sample sessions from a recorded triage (made with the course
    model on the same synthetic sessions) so the Sessions page has real results. Unchanged sessions are
    then skipped, so no model is needed."""
    dest = config.STATE_DIR / "cache_sample.json"
    src = config.SAMPLE_DIR / "recorded_triage.json"
    if config.DATA_MODE == "sample" and not dest.exists() and src.exists():
        config.STATE_DIR.mkdir(exist_ok=True)
        dest.write_bytes(src.read_bytes())


def do_refresh():
    if not _lock.acquire(blocking=False):
        return  # one refresh at a time; a second click while one runs is a no-op
    _state["refreshing"] = True
    try:
        if not config.has_key():
            _state["error"] = "No OPENAI_API_KEY found in .env (this folder or the one above). Showing cached results only."
            seed_sample_cache()
        snap = refresh(Options(mode=config.DATA_MODE))
        _state["snapshot"] = snap
        _state["error"] = None if config.has_key() else _state["error"]
    except Exception as e:  # the page must keep working when a refresh fails
        _state["error"] = f"Refresh failed: {type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
    finally:
        _state["refreshing"] = False
        _state["last_refresh"] = datetime.now(timezone.utc).isoformat()
        _lock.release()


def do_map():
    if not _map_lock.acquire(blocking=False):
        return
    _map["building"] = True
    try:
        _map["map"] = refresh_map(config.DATA_MODE)
        _map["error"] = None
    except Exception as e:  # the monitor keeps working when the map fails
        _map["error"] = f"Map failed: {type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
    finally:
        _map["building"] = False
        _map_lock.release()


def loop():
    while True:
        do_refresh()
        time.sleep(config.REFRESH_SECONDS)


def map_loop():
    while True:
        do_map()
        time.sleep(max(config.REFRESH_SECONDS, 120))


def list_traces(limit=30):
    if not TRACE_DIR.exists():
        return []
    out = []
    for p in sorted(TRACE_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        out.append({"id": t["id"], "mode": t.get("mode"), "tokens": t.get("tokens"), "usd": t.get("usd"),
                    "agents": sum(1 for n in t["nodes"] if n["kind"] == "agent")})
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text", "application/json")) else ""))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    def _run_route(self, path):
        """/api/runs/<id>[/<what>] -> (run, what) or (None, None)."""
        parts = path[len("/api/runs/"):].split("/")
        run = runs.get(parts[0]) if parts and parts[0] else None
        return run, (parts[1] if len(parts) > 1 else "")

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/runs":
            return self._send(200, {"runs": runs.list_runs(), "workers": workers.choices(), "has_key": config.has_key(),
                                    "model": config.MODEL, "max_run_usd": config.MAX_RUN_USD,
                                    "demo": {"goal": runs.demo.Scenario().goal, "budget_usd": runs.demo.Scenario().budget_usd,
                                             "repo_name": runs.demo.REPO_NAME},
                                    "self_cost": breaker.status()})
        if u.path.startswith("/api/runs/"):
            run, what = self._run_route(u.path)
            if not run:
                return self._send(404, {"error": "no such run"})
            if what == "":
                return self._send(200, run.view())
            if what == "map":
                try:
                    return self._send(200, runmap.build(run.view()))
                except Exception as e:
                    traceback.print_exc()
                    return self._send(200, {"modules": [], "edges": [], "error": f"map failed: {e}"})
            return self._send(404, {"error": "not found"})
        if u.path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html")
        if u.path.startswith("/static/"):
            p = (STATIC / u.path[len("/static/"):]).resolve()
            if STATIC.resolve() in p.parents and p.is_file():
                ctype = {"js": "text/javascript", "css": "text/css", "png": "image/png", "svg": "image/svg+xml"}.get(p.suffix[1:], "text/plain")
                return self._send(200, p.read_bytes(), ctype)
            return self._send(404, {"error": "not found"})
        if u.path == "/api/snapshot":
            return self._send(200, {**(_state["snapshot"] or {}), "error": _state["error"],
                                    "refreshing": _state["refreshing"], "last_refresh": _state["last_refresh"],
                                    "self_cost": breaker.status(), "model": config.MODEL,
                                    "caps": {"daily_usd": config.DAILY_USD_CAP, "calls_per_hour": config.CALLS_PER_HOUR_CAP,
                                             "refresh_seconds": config.REFRESH_SECONDS}})
        if u.path == "/api/map":
            return self._send(200, {**(_map["map"] or {}), "error": _map["error"], "building": _map["building"]})
        if u.path == "/api/traces":
            return self._send(200, list_traces())
        if u.path == "/api/trace":
            tid = (q.get("id") or [""])[0]
            p = TRACE_DIR / f"{tid}.json"
            if not tid or "/" in tid or "\\" in tid or not p.exists():
                return self._send(404, {"error": "no such trace"})
            return self._send(200, json.loads(p.read_text(encoding="utf-8")))
        if u.path == "/api/replay":
            p = config.SAMPLE_DIR / "replays" / "dark_mode_toggle.json"
            return self._send(200, json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})
        if u.path == "/api/evals":
            p = config.ROOT / "evals" / "results.json"
            return self._send(200, json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/runs":
            body = self._body()
            if body is None:
                return self._send(400, {"error": "bad json"})
            try:
                run = runs.create(body.get("goal"), repo=body.get("repo"), budget_usd=body.get("budget_usd"),
                                  worker=body.get("worker") or "demo", max_parallel=body.get("max_parallel") or 3,
                                  auto_run=bool(body.get("auto_run")))
            except (runs.RunError, runs.worktrees.GitError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(201, run.view())
        if u.path.startswith("/api/runs/"):
            run, what = self._run_route(u.path)
            if not run:
                return self._send(404, {"error": "no such run"})
            body = self._body()
            if body is None:
                return self._send(400, {"error": "bad json"})
            try:
                if what == "action":
                    run.act(str(body.get("action")), node=body.get("node"), amount=body.get("amount") or 0)
                    return self._send(200, run.view())
                if what == "delete":
                    runs.delete(run.id)
                    return self._send(200, {"ok": True})
            except (runs.RunError, runs.worktrees.GitError) as e:
                return self._send(400, {"error": str(e)})
            return self._send(404, {"error": "not found"})
        if u.path == "/api/refresh":
            threading.Thread(target=do_refresh, daemon=True).start()
            threading.Thread(target=do_map, daemon=True).start()
            return self._send(202, {"ok": True})
        if u.path == "/api/action":
            # Lucidity never stops an agent itself. It records what the owner decided so the
            # report can count interventions; the owner does the pause/stop in their terminal.
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(min(n, 10000)) or b"{}")
            except ValueError:
                return self._send(400, {"error": "bad json"})
            row = {"ts": datetime.now(timezone.utc).isoformat(), "session_id": str(body.get("session_id"))[:80],
                   "action": str(body.get("action"))[:30], "mode": config.DATA_MODE}
            config.LOG_DIR.mkdir(exist_ok=True)
            with ACTIONS_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            return self._send(200, {"ok": True})
        return self._send(404, {"error": "not found"})


class Server(ThreadingHTTPServer):
    # On Windows, address reuse lets a second server bind a port that is already serving,
    # so the browser could show some other program's page. Fail loudly instead.
    allow_reuse_address = os.name != "nt"


def main():
    try:
        srv = Server(("127.0.0.1", config.PORT), Handler)
    except OSError:
        sys.exit(f"Port {config.PORT} is already in use. Pick another one, for example:\n"
                 f"  LUCIDITY_PORT=8800 python app.py        (Windows PowerShell: $env:LUCIDITY_PORT=\"8800\"; python app.py)")
    threading.Thread(target=loop, daemon=True).start()
    threading.Thread(target=map_loop, daemon=True).start()
    url = f"http://127.0.0.1:{config.PORT}"
    print(f"Lucidity on {url}  (data: {config.DATA_MODE}, model: {config.MODEL}, env: {config.ENV_PATH})")
    if not os.environ.get("LUCIDITY_NO_BROWSER"):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
