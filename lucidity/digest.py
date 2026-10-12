"""Plain-code facts about a session, and the delimited, redacted text the agents read."""
from collections import Counter

from .readers import age_minutes, parse_ts
from .redact import redact

TAIL_EVENTS = 14


def facts(s, now):
    """Numbers a program can compute without a model."""
    idle = age_minutes(s.last_activity, now)
    recent = [t for t in s.tool_call_times if (a := age_minutes(t, now)) is not None and a <= 10]
    repeats = Counter(s.tool_call_keys).most_common(1)
    return {
        "minutes_since_last_activity": round(idle, 1) if idle is not None else None,
        "tool_calls_total": len(s.tool_call_times),
        "tool_calls_last_10_min": len(recent),
        "most_repeated_tool_call_count": repeats[0][1] if repeats else 0,
        "open_tool_call": s.open_tool_call,
        "open_tool_call_waiting_min": round(idle, 1) if s.open_tool_call and idle is not None else 0,
        "last_event_kind": s.events[-1].kind if s.events else None,
        "pending_question": redact(s.pending_question),
        "tokens_total": s.tokens["input"] + s.tokens["output"],
        "usd": s.usd,
    }


def _neutralize(text):
    # transcript text can't close our data tags or open new ones
    return text.replace("</session_data", "</ session_data").replace("<session_data", "< session_data")


def render_events(events):
    lines = []
    for e in events:
        err = " ERROR" if e.is_error else ""
        lines.append(f"[{e.id}] {e.kind}{err}{(' ' + e.tool) if e.tool and e.kind != 'ran' else ''}: {_neutralize(redact(e.text))[:600]}")
    return "\n".join(lines)


def session_block(s, now, tail=TAIL_EVENTS):
    f = facts(s, now)
    first = _neutralize(redact(s.first_prompt or ""))[:400]
    fact_lines = "\n".join(f"{k}: {v}" for k, v in f.items())
    return (f"session {s.id} ({s.tool}, project {s.project})\n"
            f"computed by Lucidity from the log, trustworthy:\n{fact_lines}\n"
            f'<session_data id="{s.id}">\n'
            f"task (first thing the user typed): {first}\n"
            f"last {min(tail, len(s.events))} of {s.event_count} events:\n{render_events(s.events[-tail:])}\n"
            f"</session_data>")
