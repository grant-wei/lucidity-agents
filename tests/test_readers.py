"""Transcript readers: the sample sessions parse the way the generator built them, and the
Claude Code and Codex formats are read correctly on small hand-written logs."""
import json
import os
import time

import pytest

from lucidity import readers
from lucidity.cost import model_cost
from lucidity.readers import age_minutes, clock, load_sessions, parse_ts, read_claude, read_codex

LABELS = json.loads((readers.config.SAMPLE_DIR / "labels.json").read_text(encoding="utf-8"))


def write_jsonl(path, rows):
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def by_scenario():
    return {s.scenario: s for s in load_sessions("sample")}


# ---------- sample data ----------

def test_every_sample_session_loads_with_its_label():
    sessions = load_sessions("sample")
    assert len(sessions) == 8
    assert sorted(s.tool for s in sessions) == ["claude"] * 5 + ["codex"] * 3
    labelled = {k for k in LABELS if not k.startswith("_")}
    assert {s.id for s in sessions} == labelled
    for s in sessions:
        assert s.scenario == LABELS[s.id]["scenario"]
        assert s.first_prompt and s.project and s.model and s.last_activity


def test_sessions_are_newest_first():
    acts = [s.last_activity for s in load_sessions("sample")]
    assert acts == sorted(acts, reverse=True)


def test_waiting_on_approval_shows_as_an_open_tool_call():
    s = by_scenario()["waiting_permission"]
    assert s.open_tool_call == "Bash"
    assert s.pending_question is None


def test_codex_question_is_pending():
    s = by_scenario()["injection"]
    assert s.pending_question.startswith("Should escalation go to")
    assert s.open_tool_call == "request_user_input"


def test_finished_sessions_have_nothing_open():
    for name in ("finished", "false_done", "secret_leak"):
        s = by_scenario()[name]
        assert s.open_tool_call is None and s.pending_question is None


def test_long_sessions_keep_only_the_last_events():
    s = by_scenario()["runaway"]
    assert s.event_count > readers.KEEP_EVENTS
    assert len(s.events) == readers.KEEP_EVENTS
    assert s.events[-1].id == f"e{s.event_count}"
    assert len(s.tool_call_keys) > readers.KEEP_EVENTS     # detectors still see every call


def test_event_ids_are_unique_and_in_order():
    for s in load_sessions("sample"):
        nums = [int(e.id[1:]) for e in s.events]
        assert nums == sorted(nums) and len(set(nums)) == len(nums)


def test_sample_clock_is_frozen():
    assert clock("sample") == parse_ts(LABELS["_meta"]["sample_now"])


# ---------- Claude Code format ----------

def claude_rows():
    usage = {"input_tokens": 100, "cache_read_input_tokens": 900, "cache_creation_input_tokens": 50, "output_tokens": 40}
    return [
        {"type": "user", "timestamp": "2026-10-20T14:00:00Z", "cwd": "/home/a/proj-x", "isMeta": True,
         "message": {"content": "<system-reminder>ignore me</system-reminder>"}},
        {"type": "user", "timestamp": "2026-10-20T14:00:01Z", "message": {"content": "fix the login bug"}},
        "{not json",
        {"type": "assistant", "timestamp": "2026-10-20T14:00:05Z",
         "message": {"id": "m1", "model": "claude-sonnet-5", "usage": usage,
                     "content": [{"type": "text", "text": "Looking."},
                                 {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "pytest -q"}}]}},
        # the same message id again (Claude Code writes one record per content block): count tokens once
        {"type": "assistant", "timestamp": "2026-10-20T14:00:05Z",
         "message": {"id": "m1", "model": "claude-sonnet-5", "usage": usage, "content": []}},
        {"type": "user", "timestamp": "2026-10-20T14:00:09Z",
         "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True,
                                  "content": [{"type": "text", "text": "1 failed"}]}]}},
        {"type": "assistant", "timestamp": "2026-10-20T14:00:12Z",
         "message": {"id": "m2", "model": "claude-sonnet-5",
                     "content": [{"type": "tool_use", "id": "t2", "name": "AskUserQuestion",
                                  "input": {"prompt": "Which login flow?"}}]}},
    ]


def test_claude_transcript(tmp_path):
    s = read_claude(write_jsonl(tmp_path / "abc.jsonl", claude_rows()))
    assert s.id == "abc" and s.tool == "claude" and s.project == "proj-x"
    assert s.first_prompt == "fix the login bug"          # the system reminder isn't a prompt
    assert [e.kind for e in s.events] == ["asked", "said", "ran", "result", "question"]
    result = s.events[3]
    assert result.is_error and result.tool == "Bash" and result.text == "1 failed"
    assert s.tokens == {"input": 1050, "cached": 900, "cache_write": 50, "output": 40}
    assert s.usd == round(model_cost("claude-sonnet-5", 1050, 900, 40, 50), 4)
    assert s.open_tool_call == "AskUserQuestion"
    assert s.pending_question.startswith("AskUserQuestion Which login flow?")
    assert s.started == "2026-10-20T14:00:00Z" and s.last_activity == "2026-10-20T14:00:12Z"


def test_answered_tool_call_is_not_open(tmp_path):
    s = read_claude(write_jsonl(tmp_path / "a.jsonl", claude_rows()[:6]))
    assert s.open_tool_call is None and s.pending_question is None


@pytest.mark.parametrize("content, expected", [
    ("plain words", "plain words"),
    ("<command-name>/review</command-name><command-args>pr 12</command-args>", "/review pr 12"),
    ("<task-notification>done</task-notification>", None),
    ("This session is being continued from a previous conversation", None),
    ("   ", None),
    ("<pasted_content id='x'>pasted</pasted_content> then mine", None),
    ("mine <system-reminder>noise</system-reminder>", "mine noise"),
])
def test_what_counts_as_a_human_prompt(content, expected):
    assert readers._human_prompt({"type": "user", "message": {"content": content}}) == expected


def test_large_file_reads_only_the_tail(tmp_path, monkeypatch):
    rows = claude_rows()[1:2] * 400 + claude_rows()[3:]
    path = write_jsonl(tmp_path / "big.jsonl", rows)
    monkeypatch.setattr(readers, "TAIL_BYTES", 2000)
    s = read_claude(path)
    assert s.event_count < 400                               # the head was skipped
    assert s.first_prompt == "fix the login bug"             # but the first prompt is still found
    assert s.open_tool_call == "AskUserQuestion"


# ---------- Codex format ----------

def codex_rows():
    return [
        {"timestamp": "2026-10-20T14:00:00Z", "type": "session_meta", "payload": {"id": "cx-1", "cwd": "C:\\code\\proj-y"}},
        {"timestamp": "2026-10-20T14:00:00Z", "type": "turn_context", "payload": {"model": "gpt-6-codex"}},
        {"timestamp": "2026-10-20T14:00:01Z", "type": "response_item",
         "payload": {"type": "message", "role": "user",
                     "content": [{"type": "input_text", "text": "<environment_context>cwd</environment_context>"}]}},
        {"timestamp": "2026-10-20T14:00:02Z", "type": "response_item",
         "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "add a cache"}]}},
        {"timestamp": "2026-10-20T14:00:03Z", "type": "response_item",
         "payload": {"type": "function_call", "name": "shell", "call_id": "c1",
                     "arguments": json.dumps({"command": ["pytest", "-q"]})}},
        {"timestamp": "2026-10-20T14:00:04Z", "type": "response_item",
         "payload": {"type": "function_call_output", "call_id": "c1",
                     "output": json.dumps({"output": "2 failed", "metadata": {"exit_code": 1}})}},
        {"timestamp": "2026-10-20T14:00:05Z", "type": "event_msg",
         "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 500, "cached_input_tokens": 100, "output_tokens": 20}}}},
        {"timestamp": "2026-10-20T14:00:06Z", "type": "event_msg",
         "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 900, "cached_input_tokens": 300, "output_tokens": 50}}}},
        {"timestamp": "2026-10-20T14:00:07Z", "type": "response_item",
         "payload": {"type": "function_call", "name": "request_user_input", "call_id": "c2",
                     "arguments": json.dumps({"questions": [{"question": "Redis or in-memory?"}]})}},
    ]


def test_codex_rollout(tmp_path):
    s = read_codex(write_jsonl(tmp_path / "rollout.jsonl", codex_rows()))
    assert s.id == "cx-1" and s.tool == "codex" and s.project == "proj-y" and s.model == "gpt-6-codex"
    assert s.first_prompt == "add a cache"                  # environment context isn't a prompt
    assert [e.kind for e in s.events] == ["asked", "ran", "result", "question"]
    assert s.events[1].text == "shell pytest -q"
    assert s.events[2].is_error and s.events[2].text == "2 failed"
    # totals are cumulative: the last reading wins, it is not summed
    assert s.tokens == {"input": 900, "cached": 300, "cache_write": 0, "output": 50}
    assert s.usd == round(model_cost("gpt-6-codex", 900, 300, 50), 4)
    assert s.pending_question == "Redis or in-memory?"
    assert s.open_tool_call == "request_user_input"


def test_codex_plain_text_exit_code_is_an_error(tmp_path):
    rows = codex_rows()[:5] + [{"timestamp": "2026-10-20T14:00:04Z", "type": "response_item",
                                "payload": {"type": "function_call_output", "call_id": "c1",
                                            "output": "Process exited with code 2"}}]
    s = read_codex(write_jsonl(tmp_path / "r.jsonl", rows))
    assert s.events[-1].is_error and s.open_tool_call is None


# ---------- local discovery ----------

def test_local_mode_finds_recent_sessions_only(tmp_path, monkeypatch):
    claude_home, codex_home = tmp_path / "claude", tmp_path / "codex"
    proj = claude_home / "projects" / "p"
    proj.mkdir(parents=True)
    fresh = write_jsonl(proj / "fresh.jsonl", claude_rows())
    stale = write_jsonl(proj / "stale.jsonl", claude_rows())
    old = time.time() - 10 * 86400
    os.utime(stale, (old, old))
    day = codex_home / "sessions" / "2026" / "10" / "20"
    day.mkdir(parents=True)
    write_jsonl(day / "rollout-1.jsonl", codex_rows())
    monkeypatch.setattr(readers, "CLAUDE_HOME", claude_home)
    monkeypatch.setattr(readers, "CODEX_HOME", codex_home)
    found = {(tool, p.name) for tool, p in readers.local_paths(days=3)}
    assert found == {("claude", "fresh.jsonl"), ("codex", "rollout-1.jsonl")}
    sessions = load_sessions("local")
    assert {s.id for s in sessions} == {"fresh", "cx-1"}
    assert all(s.scenario is None for s in sessions)       # sample labels never leak into local mode
    assert fresh.exists()


def test_local_mode_with_no_agent_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(readers, "CLAUDE_HOME", tmp_path / "none")
    monkeypatch.setattr(readers, "CODEX_HOME", tmp_path / "none")
    assert load_sessions("local") == []


# ---------- time helpers ----------

def test_timestamps():
    assert parse_ts("2026-10-20T15:00:00.000Z").utcoffset().total_seconds() == 0
    assert parse_ts(None) is None and parse_ts("yesterday") is None
    assert age_minutes("2026-10-20T14:30:00Z", parse_ts("2026-10-20T15:00:00Z")) == 30
    assert age_minutes(None) is None
