"""Permitted account attributes, excluding protected traits and identifiers."""
MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
NAMES = (["credit_limit"] + [f"status_{m}" for m in MONTHS]
         + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS])


def features(customer):
    """One list of numeric account-history values, in NAMES order."""
    return [customer[name] for name in NAMES]
