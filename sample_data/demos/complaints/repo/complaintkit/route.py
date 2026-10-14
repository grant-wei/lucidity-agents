from concurrent.futures import ThreadPoolExecutor

from . import labels, llm, prompt

LABELS = ("credit_reporting", "debt_collection", "credit_card", "checking_savings", "money_transfer", "mortgage")


def route(text):
    """The product label for one complaint."""
    return labels.parse(llm.complete(prompt.build(text)))


def route_many(texts, workers=12):
    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(route, texts))
