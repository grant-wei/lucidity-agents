"""Non-sensitive account history available as of September 2005."""
NAMES = ["credit_limit", "education"] + [f"status_{m}" for m in ("sep", "aug", "jul", "jun", "may", "apr")] + [f"bill_{m}" for m in ("sep", "aug", "jul", "jun", "may", "apr")] + [f"paid_{m}" for m in ("sep", "aug", "jul", "jun", "may", "apr")]


def features(customer):
    """One list of permitted numeric account features, in NAMES order."""
    return [customer[name] for name in NAMES]
