"""Read Claude Code and Codex session transcripts into one Session shape.

Ported from the private Lucidity collector, minus everything Windows-specific:
no process tables, window titles or psutil. A session is whatever its transcript
file says, so the same code reads a viewer's real sessions and the sample data.
"""
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from . import touches
from .cost import model_cost

TAIL_BYTES = 6_000_000
KEEP_EVENTS = 80
CLAUDE_HOME = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
CODEX_HOME = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")

_TAG_RE = re.compile(r"</?(?:pasted_content|system-reminder)[^>]*>")
_CMD_RE = re.compile(r"<command-name>(.*?)</command-name>(?:.*?<command-args>(.*?)</command-args>)?", re.S)


@dataclass
class Event:
    id: str
    t: str | None
    kind: str          # asked | said | ran | result | question
    text: str
    tool: str | None = None
    is_error: bool = False


@dataclass
class Session:
    id: str
    tool: str                      # claude | codex
    project: str
    path: str
    first_prompt: str | None = None
    model: str | None = None
    events: list = field(default_factory=list)          # last KEEP_EVENTS Event
    pending_question: str | None = None
    open_tool_call: str | None = None                   # a tool call with no result yet
    last_activity: str | None = None
    started: str | None = None
    tokens: dict = field(default_factory=lambda: {"input": 0, "cached": 0, "cache_write": 0, "output": 0})
    usd: float = 0.0
    tool_call_times: list = field(default_factory=list)  # every tool call timestamp (for rate detectors)
    tool_call_keys: list = field(default_factory=list)   # "name|args" per call (for repeat detectors)
    cost_points: list = field(default_factory=list)      # [timestamp, usd] per model turn (for recent spend)
    touches: list = field(default_factory=list)          # file edits, see touches.py, each with t and event id
    cwd: str | None = None
    event_count: int = 0
    scenario: str | None = None    # sample data only: what the generator built it to be

    def to_dict(self, events=True):
        d = asdict(self)
        d.pop("tool_call_times")
        d.pop("tool_call_keys")
        d.pop("cost_points")
        d.pop("touches")
        if not events:
            d.pop("events")
        return d


def _clip(text, n=1200):
    text = " ".join(str(text).split()) if len(str(text)) > n else str(text)
    return text[:n]


# ---------- Claude Code ----------

def _human_prompt(d):
    """Text of a user record if a person typed it, else None."""
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        text = c
    elif isinstance(c, list):
        text = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    else:
        return None
    text = text.strip()
    if not text or d.get("isMeta"):
        return None
    if text.startswith("<") and not text.startswith("<command-name>"):
        return None  # skill loads, command output, task notifications
    m = _CMD_RE.search(text)
    if m:
        text = (m.group(1) + " " + (m.group(2) or "")).strip()
    text = _TAG_RE.sub("", text).strip()
    if text.startswith("This session is being continued"):
        return None
    return text[:600] or None


def _tool_hint(blk):
    inp = blk.get("input") or {}
    hint = (inp.get("description") or inp.get("command") or inp.get("file_path")
            or inp.get("pattern") or inp.get("query") or inp.get("url") or inp.get("prompt") or "")
    return f"{blk.get('name')} {' '.join(str(hint).split())[:200]}".strip()


def _result_text(blk):
    c = blk.get("content")
    if isinstance(c, list):
        c = "\n".join(p.get("text", "") for p in c if isinstance(p, dict))
    return str(c or "")


def _read_lines(path):
    size = path.stat().st_size
    with open(path, "rb") as fh:
        if size > TAIL_BYTES:
            fh.seek(size - TAIL_BYTES)
            fh.readline()
        raw = fh.read().decode("utf-8", "replace")
    return raw.splitlines(), size > TAIL_BYTES


def _first_human(path, parse):
    with open(path, "rb") as fh:
        for _ in range(400):
            line = fh.readline()
            if not line:
                break
            try:
                d = json.loads(line)
            except ValueError:
                continue
            text = parse(d)
            if text:
                return text
    return None


def read_claude(path):
    path = Path(path)
    lines, _ = _read_lines(path)
    s = Session(id=path.stem, tool="claude", project="", path=str(path))
    events, open_calls, seen_msgs = [], {}, set()
    n = 0
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        typ, ts = d.get("type"), d.get("timestamp")
        if ts:
            s.started = s.started or ts
            s.last_activity = ts
        if d.get("cwd") and not s.cwd:
            s.cwd = d["cwd"]
        msg = d.get("message") or {}
        if typ == "user":
            text = _human_prompt(d)
            if text:
                n += 1
                events.append(Event(f"e{n}", ts, "asked", text))
                open_calls.clear()
            for blk in msg.get("content") or [] if isinstance(msg.get("content"), list) else []:
                if isinstance(blk, dict) and blk.get("type") == "tool_result":
                    call = open_calls.pop(blk.get("tool_use_id"), None)
                    n += 1
                    events.append(Event(f"e{n}", ts, "result", _clip(_result_text(blk)),
                                        tool=call, is_error=bool(blk.get("is_error"))))
        elif typ == "assistant":
            s.model = msg.get("model") or s.model
            mid = msg.get("id")
            u = msg.get("usage") or {}
            if u and mid not in seen_msgs:
                seen_msgs.add(mid)
                fresh = u.get("input_tokens", 0) or 0
                cr = u.get("cache_read_input_tokens", 0) or 0
                cw = u.get("cache_creation_input_tokens", 0) or 0
                s.tokens["input"] += fresh + cr + cw
                s.tokens["cached"] += cr
                s.tokens["cache_write"] += cw
                s.tokens["output"] += u.get("output_tokens", 0) or 0
                usd = model_cost(s.model, fresh + cr + cw, cr, u.get("output_tokens", 0) or 0, cw)
                s.usd += usd
                s.cost_points.append([ts, usd])
            for blk in msg.get("content") or []:
                if not isinstance(blk, dict):
                    continue
                if blk.get("type") == "text" and len(blk.get("text", "").strip()) >= 2:
                    n += 1
                    events.append(Event(f"e{n}", ts, "said", _clip(blk["text"].strip())))
                elif blk.get("type") == "tool_use":
                    n += 1
                    hint = _tool_hint(blk)
                    kind = "question" if blk.get("name") == "AskUserQuestion" else "ran"
                    events.append(Event(f"e{n}", ts, kind, hint, tool=blk.get("name")))
                    for tch in touches.from_claude(blk.get("name"), blk.get("input")):
                        s.touches.append({**tch, "t": ts, "event": f"e{n}"})
                    open_calls[blk.get("id")] = blk.get("name")
                    s.tool_call_times.append(ts)
                    s.tool_call_keys.append(f"{blk.get('name')}|{json.dumps(blk.get('input'), sort_keys=True)[:300]}")
    s.event_count = n
    s.events = events[-KEEP_EVENTS:]
    s.first_prompt = next((e.text for e in events if e.kind == "asked"), None) or _first_human(
        path, lambda d: _human_prompt(d) if d.get("type") == "user" else None)
    if open_calls:
        name = list(open_calls.values())[-1]
        s.open_tool_call = name
        if name == "AskUserQuestion":
            q = next((e.text for e in reversed(events) if e.kind == "question"), None)
            s.pending_question = q
    s.usd = round(s.usd, 4)
    s.project = project_name(s)
    return s


# ---------- Codex ----------

def _codex_user_text(payload):
    text = "\n".join(p.get("text", "") for p in payload.get("content") or []
                     if isinstance(p, dict) and p.get("type") in ("input_text", "text")).strip()
    if not text or text.startswith(("# AGENTS.md instructions", "<environment_context>", "<user_instructions>")):
        return None
    return text[:600]


def read_codex(path):
    path = Path(path)
    lines, truncated = _read_lines(path)
    s = Session(id=path.stem, tool="codex", project="", path=str(path))
    if truncated:  # session_meta is the first line, which a tail read skips
        meta = _first_human(path, lambda d: d.get("payload") if d.get("type") == "session_meta" else None)
        if isinstance(meta, dict):
            s.id, s.cwd = meta.get("id") or s.id, meta.get("cwd")
    events, open_calls, asked = [], {}, {}
    n = 0
    last_total, last_usd = None, 0.0
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        ts = rec.get("timestamp")
        p = rec.get("payload") or {}
        if ts:
            s.started = s.started or ts
            s.last_activity = ts
        typ = rec.get("type")
        if typ == "session_meta":
            s.id = p.get("id") or s.id
            s.cwd = p.get("cwd") or s.cwd
        elif typ == "turn_context":
            s.model = p.get("model") or s.model
            s.cwd = s.cwd or p.get("cwd")
        elif typ == "event_msg" and p.get("type") == "token_count":
            tot = (p.get("info") or {}).get("total_token_usage")
            if tot:
                usd_now = model_cost(s.model, tot.get("input_tokens", 0) or 0, tot.get("cached_input_tokens", 0) or 0,
                                     tot.get("output_tokens", 0) or 0)
                if last_total is not None and usd_now > last_usd:
                    s.cost_points.append([ts, usd_now - last_usd])
                last_total, last_usd = tot, usd_now
        elif typ == "response_item":
            kind = p.get("type")
            if kind == "message" and p.get("role") == "user":
                text = _codex_user_text(p)
                if text:
                    n += 1
                    events.append(Event(f"e{n}", ts, "asked", text))
                    asked.clear()
                    open_calls.clear()
            elif kind == "message" and p.get("role") == "assistant":
                text = "\n".join(c.get("text", "") for c in p.get("content") or []
                                 if isinstance(c, dict) and c.get("type") == "output_text").strip()
                if text:
                    n += 1
                    events.append(Event(f"e{n}", ts, "said", _clip(text)))
            elif kind in ("function_call", "custom_tool_call"):
                name = p.get("name") or "tool"
                args = p.get("arguments") if kind == "function_call" else p.get("input")
                parsed = args
                if isinstance(args, str):
                    try:
                        parsed = json.loads(args)
                    except ValueError:
                        parsed = args
                if name in ("request_user_input", "request_user_input_async"):
                    qs = parsed.get("questions") if isinstance(parsed, dict) else None
                    q = (qs[0].get("question") or qs[0].get("title")) if qs else "Question"
                    n += 1
                    events.append(Event(f"e{n}", ts, "question", str(q)[:400], tool=name))
                    asked[p.get("call_id")] = q
                else:
                    if isinstance(parsed, dict):
                        cmd = parsed.get("cmd") or parsed.get("command") or parsed
                        hint = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                    else:
                        hint = str(parsed or "")
                    n += 1
                    events.append(Event(f"e{n}", ts, "ran", f"{name} {' '.join(hint.split())[:200]}", tool=name))
                for tch in touches.from_patch_text(args if isinstance(args, str) else json.dumps(args)):
                    s.touches.append({**tch, "t": ts, "event": f"e{n}"})
                open_calls[p.get("call_id")] = name
                s.tool_call_times.append(ts)
                s.tool_call_keys.append(f"{name}|{str(args)[:300]}")
            elif kind in ("function_call_output", "custom_tool_call_output"):
                out = p.get("output")
                if isinstance(out, list):
                    out = "\n".join(o.get("text", "") for o in out if isinstance(o, dict))
                if isinstance(out, dict):
                    out = out.get("output") or json.dumps(out)
                text = str(out or "")
                try:
                    j = json.loads(text)
                    if isinstance(j, dict) and "output" in j:
                        text = str(j.get("output"))
                        is_err = (j.get("metadata") or {}).get("exit_code", 0) != 0
                    else:
                        is_err = False
                except ValueError:
                    is_err = bool(re.search(r"exit code:? [1-9]|Process exited with code [1-9]", text))
                call = open_calls.pop(p.get("call_id"), None)
                asked.pop(p.get("call_id"), None)
                n += 1
                events.append(Event(f"e{n}", ts, "result", _clip(text), tool=call, is_error=is_err))
    if last_total:
        s.tokens = {"input": last_total.get("input_tokens", 0) or 0, "cached": last_total.get("cached_input_tokens", 0) or 0,
                    "cache_write": 0, "output": (last_total.get("output_tokens", 0) or 0)}
        s.usd = round(model_cost(s.model, s.tokens["input"], s.tokens["cached"], s.tokens["output"]), 4)
    s.event_count = n
    s.events = events[-KEEP_EVENTS:]
    s.first_prompt = next((e.text for e in events if e.kind == "asked"), None)
    if asked:
        s.pending_question = str(list(asked.values())[-1])
    if open_calls:
        s.open_tool_call = list(open_calls.values())[-1]
    s.project = project_name(s)
    return s


# ---------- naming ----------

_ROOTS = {}


def git_root(path):
    """The folder holding .git above a file, or None. Cached; only looks at the local disk."""
    p = Path(str(path).replace("\\", "/"))
    for folder in [p, *p.parents]:
        key = str(folder)
        if key in _ROOTS:
            return _ROOTS[key]
        try:
            if (folder / ".git").exists():
                _ROOTS[key] = folder
                return folder
        except OSError:
            return None
    return None


def project_name(s):
    """The repo a session works on: where most of its edits landed, else its working folder.
    A session started from the home folder or a folder of many repos is named after the repo it edited."""
    roots = [git_root(t["path"]) for t in s.touches]
    roots = [r for r in roots if r]
    if roots:
        best = max(set(roots), key=roots.count)
        return best.name
    if s.cwd:
        cwd = Path(s.cwd.replace("\\", "/"))
        if cwd == Path.home():
            return "~"
        return cwd.name or s.cwd
    return "(unknown)"


# ---------- discovery ----------

def _recent(paths, limit):
    paths = [p for p in paths if p.is_file()]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths[:limit]


def local_paths(limit=25, days=3):
    cutoff = datetime.now().timestamp() - days * 86400
    claude = [p for p in (CLAUDE_HOME / "projects").glob("*/*.jsonl") if p.stat().st_mtime >= cutoff] \
        if (CLAUDE_HOME / "projects").exists() else []
    codex = [p for p in (CODEX_HOME / "sessions").glob("*/*/*/*.jsonl") if p.stat().st_mtime >= cutoff] \
        if (CODEX_HOME / "sessions").exists() else []
    return [("claude", p) for p in _recent(claude, limit)] + [("codex", p) for p in _recent(codex, limit)]


def sample_paths():
    out = []
    for tool in ("claude", "codex"):
        for p in sorted((config.SAMPLE_DIR / "sessions" / tool).glob("*.jsonl")):
            out.append((tool, p))
    return out


def load_sessions(mode=None, limit=25):
    mode = mode or config.DATA_MODE
    pairs = local_paths(limit) if mode == "local" else sample_paths()
    labels = {}
    if mode != "local":
        lp = config.SAMPLE_DIR / "labels.json"
        if lp.exists():
            labels = json.loads(lp.read_text(encoding="utf-8"))
    sessions = []
    for tool, path in pairs:
        try:
            s = read_claude(path) if tool == "claude" else read_codex(path)
        except (OSError, ValueError) as e:
            print(f"skipped {path.name}: {e}")
            continue
        if not s.first_prompt and s.event_count == 0:
            continue
        lab = labels.get(path.stem)
        if lab:
            s.scenario = lab.get("scenario")
        sessions.append(s)
    sessions.sort(key=lambda s: s.last_activity or "", reverse=True)
    return sessions[:limit] if mode == "local" else sessions


def parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def age_minutes(ts, now=None):
    t = parse_ts(ts)
    if not t:
        return None
    now = now or datetime.now(timezone.utc)
    return (now - t).total_seconds() / 60


def clock(mode=None):
    """'Now' for detectors: the real time for local sessions, the frozen sample time for sample data."""
    mode = mode or config.DATA_MODE
    if mode != "local":
        lp = config.SAMPLE_DIR / "labels.json"
        if lp.exists():
            meta = json.loads(lp.read_text(encoding="utf-8")).get("_meta") or {}
            if meta.get("sample_now"):
                return parse_ts(meta["sample_now"])
    return datetime.now(timezone.utc)
