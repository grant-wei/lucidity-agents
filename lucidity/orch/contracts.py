"""Done-when contracts, checked by a program. Five kinds of condition, same as the planner writes:
  test           an allowlisted test command must exit 0 (no shell, timeout, see agents/checker.py)
  file_contains  a repo file must contain an exact string
  metric         a score printed by an allowlisted eval script must clear a threshold
                 (metric "date.f1", op ">=", value 0.9)
  no_regression  no score matching a pattern ("*.f1") may drop more than `value` below where it
                 was when the task started
  rubric         something only a reader can judge; left to the checker model, or to you"""
from fnmatch import fnmatchcase
from pathlib import Path

from ..agents.checker import run_allowlisted_command, run_eval_command

SCORED = ("metric", "no_regression")
OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}


def _num(x):
    return f"{x:.2f}" if abs(x) >= 0.1 or x == 0 else f"{x:.4f}".rstrip("0")


def label(c):
    if c["kind"] == "test":
        return f"tests pass: {c['command']}"
    if c["kind"] == "file_contains":
        return f"{c['path']} contains “{c['text']}”"
    if c["kind"] == "metric":
        return f"{c['metric']} {'≥' if c.get('op', '>=') == '>=' else '≤'} {_num(c['value'])}"
    if c["kind"] == "no_regression":
        return f"no {c['metric']} drops more than {_num(c['value'])}"
    return f"reviewer: {c['text']}"


def eval_commands(conditions):
    seen = []
    for c in conditions:
        if c["kind"] in SCORED and c["command"] not in seen:
            seen.append(c["command"])
    return seen


def contract_text(node):
    lines = [f"TASK {node['id']}: {node['title']}", node["prompt"], "", "DONE WHEN (all of these):"]
    lines += [f"- {label(c)}" for c in node["done_when"]]
    for cmd in eval_commands(node["done_when"]):
        lines.append(f"Scores come from `{cmd}`; it prints them as JSON. Run it to see where you stand.")
    return "\n".join(lines)


def _inside(root, rel):
    root = Path(root).resolve()
    p = (root / rel).resolve()
    return p if p == root or root in p.parents else None


def score(command, cwd, cache=None):
    """The eval's metrics for this folder, run once per command per check."""
    if cache is not None and command in cache:
        return cache[command]
    res = run_eval_command(command, cwd)
    if cache is not None:
        cache[command] = res
    return res


def evaluate(conditions, cwd, before=None, scores=None):
    """One result per condition: met True/False, or None for a rubric (a program can't say).
    `before` maps eval command -> its metrics when the task started (for no_regression and to show
    the change); `scores` collects this check's metrics per command."""
    out = []
    before = before or {}
    scores = {} if scores is None else scores
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
        elif c["kind"] in SCORED:
            res = score(c["command"], cwd, scores)
            if "error" in res:
                r.update(met=False, evidence=f"the eval failed: {res['error']}")
            elif c["kind"] == "metric":
                r.update(_metric(c, res["metrics"], (before.get(c["command"]) or {}).get("metrics") or {}))
            else:
                r.update(_no_regression(c, res["metrics"], (before.get(c["command"]) or {}).get("metrics")))
        else:
            r["evidence"] = "needs a reader"
        out.append(r)
    return out


def _metric(c, now, was):
    name = c["metric"]
    if name not in now:
        return {"met": False, "evidence": f"the eval printed no {name}"}
    v = now[name]
    met = OPS.get(c.get("op", ">="), OPS[">="])(v, c["value"])
    shown = _num(v)
    if not met and shown == _num(c["value"]):   # 0.847 against a 0.85 bar must not read "0.85, needs ≥ 0.85"
        shown = next((s for s in (f"{v:.{d}f}" for d in range(3, 7)) if s != f"{c['value']:.{len(s) - 2}f}"), str(v))
    change = f"{_num(was[name])} → {shown}" if name in was else f"now {shown}"
    return {"met": met, "value": v, "before": was.get(name), "evidence": change + ("" if met else f", needs {label(c).split(' ', 1)[1]}")}


def _no_regression(c, now, was):
    if was is None:
        return {"met": False, "evidence": "no starting scores to compare with"}
    names = sorted(k for k in was if fnmatchcase(k, c["metric"]))
    if not names:
        return {"met": False, "evidence": f"no metric matches {c['metric']}"}
    dropped = [(k, was[k], now.get(k)) for k in names if now.get(k) is None or now[k] < was[k] - c["value"] - 1e-9]
    if not dropped:
        return {"met": True, "evidence": f"none of {len(names)} dropped"}
    return {"met": False, "drops": [{"metric": k, "before": a, "after": b} for k, a, b in dropped],
            "evidence": "; ".join(f"{k} {_num(a)} → {'missing' if b is None else _num(b)}" for k, a, b in dropped)}


def _tail(text, n=900):
    """The useful end of test output: the summary line and the failure just above it."""
    text = text.strip()
    return text if len(text) <= n else "…" + text[-n:]
