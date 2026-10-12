"""Cost math, and the cache that keeps Lucidity's own bill near zero: an unchanged session is
never sent to the model twice."""
import json

import pytest

from lucidity import llm
from lucidity.agents import coordinator
from lucidity.cost import DEFAULT, RATES, model_cost, rates_for

from conftest import FakeModel, use_fake

M = 1_000_000


@pytest.mark.parametrize("model, key", [
    ("gpt-6-luna", "gpt-6-luna"), ("claude-opus-5-5", "opus"), ("claude-sonnet-5", "sonnet"),
    ("Claude-Haiku-5-5", "haiku"), ("gpt-5-codex", "gpt-5"), ("gpt-6-codex", "gpt-6"),
])
def test_rates_match_by_model_name(model, key):
    assert rates_for(model) == RATES[key]


def test_luna_is_not_priced_as_full_gpt_6():
    assert rates_for("gpt-6-luna") != rates_for("gpt-6")


@pytest.mark.parametrize("model", [None, "", "some-new-model"])
def test_unknown_models_fall_back_to_the_default(model):
    assert rates_for(model) == DEFAULT


def test_each_token_kind_has_its_own_price():
    assert model_cost("gpt-6-luna", M) == pytest.approx(0.10)                    # fresh input
    assert model_cost("gpt-6-luna", M, cached_tokens=M) == pytest.approx(0.01)   # all of it cached
    assert model_cost("gpt-6-luna", 0, output_tokens=M) == pytest.approx(0.50)
    assert model_cost("claude-sonnet-5", M, cache_write_tokens=M) == pytest.approx(3.75)


def test_mixed_counts_add_up():
    # 1M input of which 600K cached and 100K cache writes, plus 50K output, on Opus
    usd = model_cost("claude-opus-5-5", M, 600_000, 50_000, 100_000)
    assert usd == pytest.approx(0.3 * 5.0 + 0.6 * 0.50 + 0.1 * 6.25 + 0.05 * 25.0)


def test_bad_counts_never_go_negative_or_crash():
    assert model_cost("gpt-6-luna", 100, cached_tokens=500) >= 0
    assert model_cost("gpt-6-luna", None, None, None, None) == 0


def test_unchanged_sessions_are_not_sent_again(sandbox, monkeypatch):
    fake = use_fake(monkeypatch, FakeModel(state="working"))
    opts = coordinator.Options(mode="sample", run_checker=False)
    first = coordinator.refresh(opts)
    calls = fake.calls
    assert calls >= 1 and len(first["sessions"]) == 8
    second = coordinator.refresh(opts)
    assert fake.calls == calls                     # nothing changed, so no model calls at all
    assert len(second["sessions"]) == 8
    # every call that did happen is in the usage log with tokens and dollars
    rows = [json.loads(x) for x in llm.USAGE_LOG.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == calls and all("usd" in r and "requests" in r for r in rows)


def test_turning_the_cache_off_pays_again(sandbox, monkeypatch):
    fake = use_fake(monkeypatch, FakeModel(state="working"))
    coordinator.refresh(coordinator.Options(mode="sample", run_checker=False))
    calls = fake.calls
    coordinator.refresh(coordinator.Options(mode="sample", run_checker=False, skip_unchanged=False))
    assert fake.calls > calls
