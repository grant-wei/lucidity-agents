"""Turns the model's free-text answer into one of the six product labels."""

import re

# Match common category names and useful paraphrases, while keeping matches
# phrase-based so generic mentions of an account do not select a product.
PATTERNS = [
    ("credit_card", re.compile(r"\b(?:credit\s+cards?|store\s+cards?|retail\s+cards?|gift\s+cards?|prepaid\s+cards?|charge\s+cards?)\b", re.I)),
    ("mortgage", re.compile(r"\b(?:mortgages?|home\s+loans?|homeowners?\s+loans?|housing\s+loans?)\b", re.I)),
    ("debt_collection", re.compile(r"\b(?:debt\s+collection|collections?|collection\s+agenc(?:y|ies)|debt\s+collectors?|debt\s+collection\s+practices?|collecting\s+(?:a\s+)?debt|debt\s+recovery)\b", re.I)),
    ("credit_reporting", re.compile(r"\b(?:credit\s+(?:reports?|reporting|bureaus?)|consumer\s+reports?|credit\s+reporting\s+agenc(?:y|ies)|credit\s+file)\b", re.I)),
    ("checking_savings", re.compile(r"\b(?:checking|checkings|savings|deposit\s+accounts?|bank\s+accounts?|debit\s+cards?)\b", re.I)),
    ("money_transfer", re.compile(r"\b(?:money\s+transfers?|wire\s+transfers?|electronic\s+funds?\s+transfers?|remittances?|payment\s+apps?|peer\s+to\s+peer\s+payments?|digital\s+wallets?|payment\s+services?)\b", re.I)),
]

# If a response names multiple products, the first one it discusses is typically
# its chosen category; avoid the old fixed-order keyword precedence.
def parse(answer):
    if not answer:
        return "unknown"
    matches = []
    for label, pattern in PATTERNS:
        match = pattern.search(str(answer))
        if match:
            matches.append((match.start(), -(match.end() - match.start()), label))
    return min(matches)[2] if matches else "unknown"
