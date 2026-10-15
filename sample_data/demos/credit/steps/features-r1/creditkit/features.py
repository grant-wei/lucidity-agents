"""Permitted account-history features, as of September 2005.

Protected traits (sex, marriage and age) are deliberately excluded. Months are ordered
September through April, matching the source data and model interface.
"""
MONTHS = ("sep", "aug", "jul", "jun", "may", "apr")
NAMES = (
    "credit_limit",
    *(f"status_{m}" for m in MONTHS),
    *(f"bill_{m}" for m in MONTHS),
    *(f"paid_{m}" for m in MONTHS),
    *(f"utilization_{m}" for m in MONTHS),
    *(f"payment_fraction_{m}" for m in MONTHS),
    "status_mean", "status_worsening", "bill_change", "payment_change",
)


def features(customer):
    """One list of numbers in NAMES order."""
    bills = [customer[f"bill_{m}"] for m in MONTHS]
    paid = [customer[f"paid_{m}"] for m in MONTHS]
    statuses = [customer[f"status_{m}"] for m in MONTHS]
    limit = max(customer["credit_limit"], 1)
    utilization = [b / limit for b in bills]
    fraction = [p / max(abs(b), 1000) for p, b in zip(paid, bills)]
    return [customer["credit_limit"], *statuses, *bills, *paid, *utilization, *fraction,
            sum(statuses) / len(statuses), statuses[0] - statuses[-1],
            bills[0] - bills[-1], paid[0] - paid[-1]]
