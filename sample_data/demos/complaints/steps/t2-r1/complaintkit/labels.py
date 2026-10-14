"""Turns the model's free-text answer into one of the six product labels."""
import re

# Product names and common short forms used in answers. Keep this list focused on
# labels, rather than attempting to classify arbitrary complaint vocabulary.
ALIASES = {
    "credit card": "credit_card",
    "credit cards": "credit_card",
    "mortgage": "mortgage",
    "home loan": "mortgage",
    "home loans": "mortgage",
    "debt collection": "debt_collection",
    "debt collector": "debt_collection",
    "collections": "debt_collection",
    "credit report": "credit_reporting",
    "credit reports": "credit_reporting",
    "credit reporting": "credit_reporting",
    "credit bureau": "credit_reporting",
    "credit bureaus": "credit_reporting",
    "checking": "checking_savings",
    "savings": "checking_savings",
    "bank account": "checking_savings",
    "checking/savings": "checking_savings",
    "money transfer": "money_transfer",
    "money transfers": "money_transfer",
    "fund transfer": "money_transfer",
    "funds transfer": "money_transfer",
    "crypto account": "money_transfer",
}


def parse(answer):
    text = answer.lower().replace("-", " ")
    # A bare canonical identifier is also a valid model answer.
    canonical = {
        "credit_card": "credit_card", "mortgage": "mortgage",
        "debt_collection": "debt_collection", "credit_reporting": "credit_reporting",
        "checking_savings": "checking_savings", "money_transfer": "money_transfer",
    }
    stripped = re.sub(r"[^a-z_]+", "", text)
    if stripped in canonical:
        return canonical[stripped]

    found = set()
    for phrase, label in ALIASES.items():
        if re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text):
            found.add(label)
    # Multiple product categories in a response are not safely disambiguated by
    # arbitrary keyword order; do not guess.
    return next(iter(found)) if len(found) == 1 else "unknown"
