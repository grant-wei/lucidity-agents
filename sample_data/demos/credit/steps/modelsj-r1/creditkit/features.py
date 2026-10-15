"""Non-sensitive account history features."""
MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
NAMES = ["credit_limit", "education"] + [f"status_{m}" for m in MONTHS] + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS]


def features(customer):
    return [customer[name] for name in NAMES]
