"""Done-when contracts, checked by a program. Three kinds of condition, same as the planner writes:
  test           an allowlisted test command must exit 0 (no shell, timeout, see agents/checker.py)
  file_contains  a repo file must contain an exact string
  rubric         something only a reader can judge; left to the checker model, or to you"""
from pathlib import Path

from ..agents.checker import run_allowlisted_command


def label(c):
    if c["kind"] == "test":
        return f"tests pass: {c['command']}"
    if c["kind"] == "file_contains":
        return f"{c['path']} contains “{c['text']}”"
    return f"reviewer: {c['text']}"


def contract_text(node):
    lines = [f"TASK {node['id']}: {node['title']}", node["prompt"], "", "DONE WHEN (all of these):"]
    lines += [f"- {label(c)}" for c in node["done_when"]]
    return "\n".join(lines)


def _inside(root, rel):
    root = Path(root).resolve()
    p = (root / rel).resolve()
    return p if p == root or root in p.parents else None


def evaluate(conditions, cwd):
    """One result per condition: met True/False, or None for a rubric (a program can't say)."""
    out = []
    for c in conditions:
        r = {"kind": c["kind"], "label": label(c), "met": None, "evidence": ""}
        if c["kind"] == "test":
            res = run_allowlisted_command(c["command"], cwd)
            if res.get("refused"):
                r.update(met=False, evidence=f"refused: {res['reason']}")
            else:
                r.update(met=res.get("exit_code") == 0, evidence=_tail(res.get("output") or ""))
        elif c["kind"] == "file_contains":
            p = _inside(cwd, c["path"])
            if p is None:
                r.update(met=False, evidence="path is outside the repo")
            elif not p.is_file():
                r.update(met=False, evidence=f"{c['path']} does not exist")
            else:
                found = c["text"] in p.read_text(encoding="utf-8", errors="replace")
                r.update(met=found, evidence="found" if found else "text not found in the file")
        else:
            r["evidence"] = "needs a reader"
        out.append(r)
    return out


def _tail(text, n=900):
    """The useful end of test output: the summary line and the failure just above it."""
    text = text.strip()
    return text if len(text) <= n else "…" + text[-n:]
