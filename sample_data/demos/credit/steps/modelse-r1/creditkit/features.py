"""Permitted account-history features; protected traits and identifiers are excluded."""
NAMES = [
    "credit_limit", "education",
    "status_sep", "status_aug", "status_jul", "status_jun", "status_may", "status_apr",
    "bill_sep", "bill_aug", "bill_jul", "bill_jun", "bill_may", "bill_apr",
    "paid_sep", "paid_aug", "paid_jul", "paid_jun", "paid_may", "paid_apr",
]


def features(customer):
    """One list of numeric account features, in NAMES order."""
    return [customer[name] for name in NAMES]
