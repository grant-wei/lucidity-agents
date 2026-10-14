"""Turns the model's free-text answer into one of the six product labels."""

# checked in order; the first keyword found in the answer wins
KEYWORDS = [
    ("credit card", "credit_card"),
    ("mortgage", "mortgage"),
    ("debt", "debt_collection"),
    ("credit report", "credit_reporting"),
    ("checking", "checking_savings"),
    ("savings", "checking_savings"),
    ("transfer", "money_transfer"),
]


def parse(answer):
    answer = answer.lower()
    for word, label in KEYWORDS:
        if word in answer:
            return label
    return "unknown"
