"""Turns the model's free-text answer into one of the six product labels."""

import re

# Match category names and useful paraphrases. Keep these phrase-based so
# generic mentions of an account do not select a product.
PATTERNS = [
    ("credit_card", re.compile(r"\b(?:credit\s+cards?|store\s+cards?|retail\s+cards?|gift\s+cards?|prepaid\s+cards?|charge\s+cards?|store\s+credit\s+accounts?)\b", re.I)),
    ("mortgage", re.compile(r"\b(?:mortgages?|home\s+loans?|homeowners?\s+loans?|housing\s+loans?)\b", re.I)),
    ("debt_collection", re.compile(r"\b(?:debt\s+collection|collections?|collection\s+agenc(?:y|ies)|debt\s+collectors?|debt\s+collection\s+practices?|collecting\s+(?:a\s+)?debt|debt\s+recovery|attempts?\s+to\s+collect|past[- ]due\s+debt)\b", re.I)),
    ("credit_reporting", re.compile(r"\b(?:credit\s+(?:reports?|reporting|bureaus?)|consumer\s+reports?|credit\s+reporting\s+agenc(?:y|ies)|credit\s+file)\b", re.I)),
    ("checking_savings", re.compile(r"\b(?:checking|checkings|savings|deposit\s+accounts?|bank\s+accounts?|debit\s+cards?)\b", re.I)),
    ("money_transfer", re.compile(r"\b(?:money\s+transfers?|wire\s+transfers?|electronic\s+funds?\s+transfers?|remittances?|payment\s+apps?|peer\s+to\s+peer\s+payments?|digital\s+wallets?|payment\s+services?|funds?\s+transfers?|cash\s+apps?|zelle|venmo|paypal)\b", re.I)),
]

# When an answer explicitly identifies the requested/primary product, trust that
# span rather than an incidental product mentioned earlier in its explanation.
_EXPLICIT = re.compile(r"\b(?:primary|main|correct|relevant)\s+(?:product|category|label)\s*(?:is|:|=)\s*", re.I)


def parse(answer):
    if not answer:
        return "unknown"
    text = str(answer)
    start = _EXPLICIT.search(text)
    if start:
        text = text[start.end():]
    matches = []
    for label, pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append((match.start(), -(match.end() - match.start()), label))
    return min(matches)[2] if matches else "unknown"
