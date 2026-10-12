"""A small coding worker, used only to record the sample replay (scripts/record_replay.py).
It edits files inside one sandbox folder and can run the allowlisted test command, nothing else.
In the real product the workers are the owner's own Claude Code or Codex sessions."""
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import Agent, RunContext

from .checker import run_allowlisted_command

INSTRUCTIONS = """You are a coding agent working in a small repo. Do the task you are given, then
check your work against its done-when conditions (run the tests if a condition is a test).
Keep changes small. When finished, reply with two sentences: what you changed, and whether the
conditions pass."""


@dataclass
class Deps:
    root: Path
    log: list = field(default_factory=list)


agent = Agent(output_type=str, instructions=INSTRUCTIONS, deps_type=Deps, name="worker")


def _safe(root, rel):
    p = (root / rel).resolve()
    if root.resolve() != p and root.resolve() not in p.parents:
        raise ValueError("path is outside the repo")
    return p


@agent.tool
def list_files(ctx: RunContext[Deps]) -> list[str]:
    """Every file in the repo, relative paths."""
    out = sorted(str(p.relative_to(ctx.deps.root)).replace("\\", "/") for p in ctx.deps.root.rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts)
    ctx.deps.log.append({"tool": "list_files", "arg": "", "result": f"{len(out)} files"})
    return out


@agent.tool
def read_file(ctx: RunContext[Deps], path: str) -> str:
    """Read a file in the repo."""
    try:
        text = _safe(ctx.deps.root, path).read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        text = f"error: {e}"
    ctx.deps.log.append({"tool": "read_file", "arg": path, "result": f"{len(text)} chars"})
    return text[:20000]


@agent.tool
def write_file(ctx: RunContext[Deps], path: str, content: str) -> str:
    """Create or overwrite a file in the repo with the full new content."""
    try:
        p = _safe(ctx.deps.root, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        msg = f"wrote {len(content)} chars"
    except (OSError, ValueError) as e:
        msg = f"error: {e}"
    ctx.deps.log.append({"tool": "write_file", "arg": path, "result": msg})
    return msg


@agent.tool
def run_tests(ctx: RunContext[Deps], command: str = "python -m pytest -q") -> dict:
    """Run the test command (allowlisted test runners only)."""
    out = run_allowlisted_command(command, ctx.deps.root)
    ctx.deps.log.append({"tool": "run_tests", "arg": command,
                         "result": f"exit {out.get('exit_code')}" if not out.get("refused") else "refused"})
    return out
