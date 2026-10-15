"""Workers: whatever does a task inside its worktree. Each one takes the task prompt and a dollar
budget, works only inside `cwd`, and reports back {"report", "usd", "error"}; what it did along
the way goes to `emit` so the page can show it live.

  demo     replays scripted edits onto the bundled toy repo. No key, no CLI, no network.
  builtin  a small pydantic-ai agent on your OpenAI key (read, write, run allowlisted tests).
  claude   your Claude Code CLI, headless (`claude -p`), with a hard --max-budget-usd.
  codex    your Codex CLI (`codex exec`), sandboxed to the worktree.

The worker never merges, never pushes and never sees the checker. The run does all of that."""
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .. import config
from ..cost import model_cost

_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ROUND_TIMEOUT_S = int(os.environ.get("LUCIDITY_WORKER_TIMEOUT") or 900)


class Worker:
    name = ""
    label = ""
    needs_key = False

    def available(self):
        return True, ""

    def run(self, node, round_no, prompt, cwd, budget_usd, emit, cancelled):
        raise NotImplementedError


class DemoWorker(Worker):
    """Copies the scenario's files for (task, round) into the worktree, paced like a real agent.
    The edits are scripted; everything after them (tests, checker, merge, budget) is real."""
    name, label = "demo", "Demo (scripted edits, no key)"

    def __init__(self, scenario, speed=None):
        self.scenario = scenario
        self.speed = float(os.environ.get("LUCIDITY_DEMO_SPEED") or 1.0) if speed is None else speed

    def run(self, node, round_no, prompt, cwd, budget_usd, emit, cancelled):
        step = self.scenario.step(node["id"], round_no)
        if step is None:
            return {"report": "The demo script has no further edits for this task.", "usd": 0.0, "error": None}
        pause = step["seconds"] * self.speed / max(1, len(step["activity"]))
        for line in step["activity"]:
            if cancelled():
                return {"report": "", "usd": 0.0, "error": "stopped"}
            emit(line)
            time.sleep(pause)
        if step["files_dir"].is_dir():
            for src in step["files_dir"].rglob("*"):
                if src.is_file():
                    dst = Path(cwd) / src.relative_to(step["files_dir"])
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
        return {"report": step["report"], "usd": step["usd"], "error": None, "changed": step.get("changed")}


class BuiltinWorker(Worker):
    name, label, needs_key = "builtin", f"Built-in agent ({config.MODEL})", True

    def available(self):
        return (True, "") if config.has_key() else (False, "needs OPENAI_API_KEY in .env")

    def run(self, node, round_no, prompt, cwd, budget_usd, emit, cancelled):
        from ..agents import worker
        from ..llm import ModelCallFailed, run_agent
        deps = worker.Deps(root=Path(cwd))
        try:
            reply, row = run_agent(worker.agent, prompt, name="worker", deps=deps, request_limit=25)
        except ModelCallFailed as e:
            for t in deps.log:
                emit(f"{t['tool']} {t['arg']}".strip())
            return {"report": "", "usd": e.row["usd"], "eval_usd": deps.eval_usd, "error": f"model call failed: {e}"}
        for t in deps.log:
            emit(f"{t['tool']} {t['arg']}".strip())
        return {"report": reply, "usd": row["usd"], "eval_usd": deps.eval_usd, "error": None}


def _cli(name):
    return shutil.which(name)


class _Process:
    """Run a CLI with the prompt on stdin, hand each stdout line to `on_line`, stop it when the
    run is stopped or the round times out."""

    def __init__(self, args, cwd, prompt, env=None):
        self.args, self.cwd, self.prompt, self.env = args, cwd, prompt, env

    def run(self, on_line, cancelled):
        p = subprocess.Popen(self.args, cwd=self.cwd, env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", creationflags=_FLAGS)
        err = []
        threading.Thread(target=lambda: err.extend(p.stderr.readlines()), daemon=True).start()
        started = time.time()

        def watchdog():
            while p.poll() is None:
                if cancelled() or time.time() - started > ROUND_TIMEOUT_S:
                    p.kill()
                    return
                time.sleep(0.5)
        threading.Thread(target=watchdog, daemon=True).start()
        try:
            p.stdin.write(self.prompt)
            p.stdin.close()
        except OSError:
            pass
        for line in p.stdout:
            try:
                on_line(json.loads(line))
            except ValueError:
                continue
        code = p.wait()
        timed_out = time.time() - started > ROUND_TIMEOUT_S
        return code, "".join(err)[-600:], timed_out


def _clean_env():
    env = dict(os.environ)
    for k in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"):
        env.pop(k, None)   # a nested CLI must not think it is inside the parent's session
    return env


class ClaudeWorker(Worker):
    name, label = "claude", "Claude Code CLI"
    TOOLS = "Read,Edit,Write,Glob,Grep,Bash(python -m pytest:*),Bash(pytest:*),Bash(npm test:*)"

    def available(self):
        return (True, "") if _cli("claude") else (False, "the claude CLI is not on PATH")

    def run(self, node, round_no, prompt, cwd, budget_usd, emit, cancelled):
        args = [_cli("claude"), "-p", "--output-format", "stream-json", "--verbose",
                "--permission-mode", "acceptEdits", "--allowedTools", self.TOOLS,
                "--max-budget-usd", f"{max(budget_usd, 0.01):.2f}"]
        state = {"report": "", "usd": 0.0, "error": None}

        def on_line(ev):
            if ev.get("type") == "assistant":
                for part in (ev.get("message") or {}).get("content") or []:
                    if part.get("type") == "tool_use":
                        inp = part.get("input") or {}
                        emit(f"{part.get('name')} {inp.get('file_path') or inp.get('command') or inp.get('pattern') or ''}".strip())
            elif ev.get("type") == "result":
                state["report"] = ev.get("result") or ""
                state["usd"] = float(ev.get("total_cost_usd") or 0)
                if ev.get("is_error"):
                    state["error"] = (ev.get("subtype") or "error").replace("_", " ")
        code, err, timed_out = _Process(args, cwd, prompt, _clean_env()).run(on_line, cancelled)
        if timed_out:
            state["error"] = f"timed out after {ROUND_TIMEOUT_S}s"
        elif code != 0 and not state["error"]:
            state["error"] = err.strip().splitlines()[-1][:200] if err.strip() else f"claude exited with {code}"
        return state


class CodexWorker(Worker):
    name, label = "codex", "Codex CLI"
    MODEL = os.environ.get("LUCIDITY_CODEX_MODEL") or "gpt-5"   # only used to estimate cost from tokens

    def available(self):
        return (True, "") if _cli("codex") else (False, "the codex CLI is not on PATH")

    def run(self, node, round_no, prompt, cwd, budget_usd, emit, cancelled):
        args = [_cli("codex"), "exec", "--json", "--cd", str(cwd), "--sandbox", "workspace-write", "--skip-git-repo-check", "-"]
        state = {"report": [], "usd": 0.0, "error": None}

        def on_line(ev):
            t = ev.get("type")
            item = ev.get("item") or {}
            if t == "item.completed" and item.get("type") == "agent_message":
                state["report"].append(item.get("text") or "")
            elif t == "item.completed" and item.get("type") == "command_execution":
                emit(f"run {item.get('command', '')}"[:160])
            elif t == "item.completed" and item.get("type") == "file_change":
                for ch in item.get("changes") or []:
                    emit(f"edit {ch.get('path', '')}")
            elif t == "turn.completed":
                u = ev.get("usage") or {}
                state["usd"] += model_cost(self.MODEL, u.get("input_tokens", 0), u.get("cached_input_tokens", 0),
                                           u.get("output_tokens", 0))
            elif t in ("turn.failed", "error"):
                state["error"] = str(ev.get("error") or ev.get("message") or "codex turn failed")[:200]
        code, err, timed_out = _Process(args, cwd, prompt, _clean_env()).run(on_line, cancelled)
        if timed_out:
            state["error"] = f"timed out after {ROUND_TIMEOUT_S}s"
        elif code != 0 and not state["error"]:
            state["error"] = f"codex exited with {code}"
        return {"report": "\n".join(state["report"]).strip(), "usd": round(state["usd"], 6), "error": state["error"]}


LIVE = {w.name: w for w in (BuiltinWorker(), ClaudeWorker(), CodexWorker())}


def choices():
    """What the composer offers, with why a choice is unavailable."""
    out = [{"name": "demo", "label": DemoWorker.label, "ok": True, "why": ""}]
    for w in LIVE.values():
        ok, why = w.available()
        out.append({"name": w.name, "label": w.label, "ok": ok, "why": why})
    return out
