"""Permitted account-history features; protected traits are deliberately excluded."""
MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
NAMES = ["credit_limit", "education"] + [f"status_{m}" for m in MONTHS] + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS]


def features(customer):
    """One list of numbers, in NAMES order."""
    return [customer[n] for n in NAMES]
