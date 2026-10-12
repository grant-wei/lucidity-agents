"""Dollar cost from token counts. List prices in USD per million tokens.

gpt-6-luna: $0.10 input, $0.01 cached input, $0.50 output (OpenAI list price, Oct 2026).
Claude rates follow Anthropic's list prices; cache writes bill at 1.25x input.
Codex sessions are billed at GPT-5 list prices unless the session names another model."""

# model substring -> (input, cached_input, output, cache_write)
RATES = {
    "gpt-6-luna": (0.10, 0.01, 0.50, 0.125),
    "opus": (5.0, 0.50, 25.0, 6.25),
    "fable": (5.0, 0.50, 25.0, 6.25),
    "sonnet": (3.0, 0.30, 15.0, 3.75),
    "haiku": (1.0, 0.10, 5.0, 1.25),
    "gpt-5": (1.25, 0.125, 10.0, 1.25),
    "gpt-6": (1.25, 0.125, 10.0, 1.25),
}
DEFAULT = RATES["gpt-5"]


def rates_for(model):
    m = (model or "").lower()
    for key, rate in RATES.items():
        if key in m:
            return rate
    return DEFAULT


def model_cost(model, input_tokens, cached_tokens=0, output_tokens=0, cache_write_tokens=0):
    """OpenAI-style counts: input_tokens includes the cached ones."""
    i, c, o, w = rates_for(model)
    fresh = max(0, (input_tokens or 0) - (cached_tokens or 0) - (cache_write_tokens or 0))
    return (fresh * i + (cached_tokens or 0) * c + (output_tokens or 0) * o + (cache_write_tokens or 0) * w) / 1e6
