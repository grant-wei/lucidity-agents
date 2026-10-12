"""Every model call Lucidity makes goes through run_agent, so every call is metered,
logged to logs/usage.jsonl from the API's own usage numbers, and stopped by the budget breaker."""
import json
import time
from datetime import datetime, timezone

from pydantic_ai import capture_run_messages
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from . import config
from .cost import model_cost
from .guard import breaker

USAGE_LOG = config.LOG_DIR / "usage.jsonl"
_model = None


def model():
    global _model
    if _model is None:
        _model = OpenAIResponsesModel(config.MODEL, provider=OpenAIProvider())
    return _model


SETTINGS = OpenAIResponsesModelSettings(openai_reasoning_effort="low", max_tokens=4000)


def log_usage(row):
    config.LOG_DIR.mkdir(exist_ok=True)
    with open(USAGE_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


class ModelCallFailed(Exception):
    """The model kept returning output that didn't fit the schema. The spend is still logged in .row."""

    def __init__(self, reason, row):
        super().__init__(reason)
        self.row = row


def _row(name, refresh_id, started, requests, tool_calls, inp, cached, out):
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent": name,
        "model": config.MODEL,
        "refresh_id": refresh_id,
        "requests": requests,
        "tool_calls": tool_calls,
        "input_tokens": inp,
        "cached_input_tokens": cached,
        "output_tokens": out,
        "latency_s": round(time.perf_counter() - started, 2),
    }
    row["usd"] = round(model_cost(config.MODEL, inp, cached, out), 6)
    return row


def run_agent(agent, prompt, *, name, deps=None, refresh_id=None, request_limit=8):
    """Run a pydantic-ai agent and return (output, usage_row). Raises BudgetExceeded before
    spending anything when Lucidity is over its own caps, and ModelCallFailed (spend still logged)
    when the model's output never fits the schema."""
    breaker.check()
    started = time.perf_counter()
    with capture_run_messages() as messages:
        try:
            result = agent.run_sync(prompt, deps=deps, model=model(), model_settings=SETTINGS,
                                    usage_limits=UsageLimits(request_limit=request_limit))
        except (UnexpectedModelBehavior, UsageLimitExceeded) as e:
            rs = [m.usage for m in messages if isinstance(m, ModelResponse)]
            row = _row(name, refresh_id, started, len(rs), 0, sum(r.input_tokens for r in rs),
                       sum(r.cache_read_tokens or 0 for r in rs), sum(r.output_tokens for r in rs))
            row["failed"] = str(e)[:200]
            log_usage(row)
            breaker.record(row)
            raise ModelCallFailed(str(e), row) from e
    u = result.usage() if callable(result.usage) else result.usage
    row = _row(name, refresh_id, started, u.requests, u.tool_calls, u.input_tokens, u.cache_read_tokens or 0, u.output_tokens)
    log_usage(row)
    breaker.record(row)
    return result.output, row
