"""Watchdog detectors. These are plain code, so the flags are exact: every sample session gets
the flags its label says, and each threshold trips at its number and not one below."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from lucidity import config
from lucidity.agents import watchdog
from lucidity.readers import Event, Session, clock, load_sessions

LABELS = json.loads((config.SAMPLE_DIR / "labels.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def make(**kw):
    s = Session(id="s1", tool="claude", project="p", path="p.jsonl", last_activity=ago(1))
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def kinds(s):
    return [f["kind"] for f in watchdog.detect(s, NOW)]


@pytest.mark.parametrize("s", load_sessions("sample"), ids=lambda s: s.scenario)
def test_sample_sessions_get_their_labelled_flags(s):
    assert [f["kind"] for f in watchdog.detect(s, clock("sample"))] == LABELS[s.id]["flags"]


def test_runaway_sample_says_why():
    s = next(x for x in load_sessions("sample") if x.scenario == "runaway")
    reason = watchdog.detect(s, clock("sample"))[0]["reason"]
    assert "same tool call ran" in reason and "per-session cap" in reason
    name, n = watchdog.repeated_call(s)
    assert name == "Bash" and n >= watchdog.REPEAT_CALLS


# ---------- runaway thresholds ----------

def test_repeated_call_threshold():
    times = [ago(60)] * watchdog.REPEAT_CALLS            # spread out, so the rate rule stays quiet
    assert kinds(make(tool_call_keys=["Bash|curl"] * (watchdog.REPEAT_CALLS - 1), tool_call_times=times[1:])) == []
    assert kinds(make(tool_call_keys=["Bash|curl"] * watchdog.REPEAT_CALLS, tool_call_times=times)) == ["runaway"]


def test_different_arguments_are_not_repeats():
    keys = [f"Bash|ls {i}" for i in range(50)]
    assert kinds(make(tool_call_keys=keys, tool_call_times=[ago(60)] * 50)) == []


def test_call_rate_threshold():
    n = int(watchdog.CALLS_PER_MIN * 10)
    keys = [f"Read|{i}" for i in range(n)]
    assert kinds(make(tool_call_keys=keys[:-1], tool_call_times=[ago(5)] * (n - 1))) == []
    assert kinds(make(tool_call_keys=keys, tool_call_times=[ago(5)] * n)) == ["runaway"]
    # the same calls more than 10 minutes ago don't count
    assert kinds(make(tool_call_keys=keys, tool_call_times=[ago(11)] * n)) == []


def test_spend_cap():
    assert kinds(make(usd=watchdog.SESSION_USD_CAP - 0.01)) == []
    assert kinds(make(usd=watchdog.SESSION_USD_CAP)) == ["runaway"]


# ---------- stalled ----------

def fail(i, text="AssertionError: expected 3 got 2 (0.41s)"):
    return Event(f"e{i}", ago(30 - i), "result", text, tool="Bash", is_error=True)


def passed(i):
    return Event(f"e{i}", ago(30 - i), "result", "12 passed in 0.8s", tool="Bash")


def test_same_failure_threshold():
    below = [fail(i) for i in range(watchdog.SAME_FAILURE - 1)]
    assert kinds(make(events=below)) == []
    at = [fail(i) for i in range(watchdog.SAME_FAILURE)]
    flags = watchdog.detect(make(events=at), NOW)
    assert [f["kind"] for f in flags] == ["stalled"]
    assert flags[0]["first_seen"] == at[0].t


def test_failures_differing_only_in_numbers_are_the_same_failure():
    evs = [fail(i, f"AssertionError: expected {i} got {i + 1} ({i}.2s)") for i in range(watchdog.SAME_FAILURE)]
    assert kinds(make(events=evs)) == ["stalled"]


def test_different_failures_are_not_a_stall():
    evs = [fail(i, f"{name}Error") for i, name in enumerate(["Key", "Type", "Value", "Name", "Index"])]
    assert kinds(make(events=evs)) == []


def test_a_passing_run_resets_the_streak():
    evs = [fail(i) for i in range(3)] + [passed(3)] + [fail(i) for i in range(4, 7)]
    assert kinds(make(events=evs)) == []


def test_edits_between_failures_are_not_progress():
    evs = []
    for i in range(watchdog.SAME_FAILURE):
        evs += [Event(f"e{2 * i}", ago(30), "ran", "Edit app.py", tool="Edit"),
                Event(f"e{2 * i + 1}", ago(30), "result", "ok", tool="Edit"), fail(2 * i + 1)]
    assert kinds(make(events=evs)) == ["stalled"]


def test_ending_on_a_pass_is_never_stalled():
    evs = [fail(i) for i in range(10)] + [passed(10)]
    assert kinds(make(events=evs)) == []


def test_runaway_takes_precedence_over_stalled():
    evs = [fail(i) for i in range(watchdog.SAME_FAILURE)]
    assert kinds(make(events=evs, usd=watchdog.SESSION_USD_CAP)) == ["runaway"]


def test_healthy_empty_session():
    assert kinds(make()) == []
    assert watchdog.repeated_call(make()) == ("", 0)
