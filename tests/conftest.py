"""Shared test helpers. The model is replaced with a scripted fake, so no test needs a key or the network."""
import re

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lucidity import config, llm, trace


class FakeModel:
    """Answers every triage call with the given state for every session and records every
    message the model was sent."""

    def __init__(self, state="finished", cite="e1"):
        self.state, self.cite, self.seen, self.calls = state, cite, [], 0

    def __call__(self, messages, info):
        self.calls += 1
        self.seen.append(repr(messages))
        text = repr(messages)
        ids = sorted(set(re.findall(r"session_id[\"']?\s*[:=]\s*[\"']?([0-9a-f-]{36})", text))
                     | set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)))
        tool = info.output_tools[0].name
        if tool_wants_explanations(info):
            args = {"items": [{"session_id": i, "why": "it keeps polling a server that never started",
                               "recommendation": "stop", "next_step": "read the server log"} for i in ids]}
            return ModelResponse(parts=[ToolCallPart(tool, args)])
        args = {"items": [{"session_id": i, "state": self.state, "warning": "",
                           "claims": [{"field": "doing_now", "text": "real claim", "event_ids": [self.cite]},
                                      {"field": "done_so_far", "text": "made-up claim", "event_ids": ["e99999"]}]}
                          for i in ids]}
        return ModelResponse(parts=[ToolCallPart(tool, args)])


def tool_wants_explanations(info):
    schema = info.output_tools[0].parameters_json_schema
    return "recommendation" in repr(schema)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(config, "DATA_MODE", "sample")
    monkeypatch.setattr(llm, "USAGE_LOG", tmp_path / "logs" / "usage.jsonl")
    monkeypatch.setattr(trace, "TRACE_DIR", tmp_path / "logs" / "traces")
    return tmp_path


def use_fake(monkeypatch, fake):
    monkeypatch.setattr(llm, "model", lambda: FunctionModel(fake))
    return fake
