"""Permitted account features as of September 2005 (excluding protected traits)."""
MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
NAMES = ["credit_limit", "education"] + [f"status_{m}" for m in MONTHS] + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS]


def features(customer):
    """One list of numbers, in NAMES order."""
    return [customer[name] for name in NAMES]
