"""Permitted account features as of September 2005 (excluding protected traits)."""
import math

MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
BASE_NAMES = ["credit_limit", "education"] + [f"status_{m}" for m in MONTHS] + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS]
# Status codes are ordinal in reality, but nonlinear effects are better represented
# by category indicators in a linear model.
STATUS_LEVELS = (-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8)
NAMES = BASE_NAMES + [f"status_{m}_is_{v}" for m in MONTHS for v in STATUS_LEVELS]
NAMES += ["recent_bill_fraction", "recent_payment_fraction", "mean_bill_fraction", "mean_payment_fraction"]


def features(customer):
    """One list of numbers, in NAMES order."""
    vals = [customer[name] for name in BASE_NAMES]
    statuses = [customer[f"status_{m}"] for m in MONTHS]
    vals += [float(s == v) for s in statuses for v in STATUS_LEVELS]
    limit = max(float(customer["credit_limit"]), 1.0)
    bills = [customer[f"bill_{m}"] for m in MONTHS]
    paid = [customer[f"paid_{m}"] for m in MONTHS]
    vals += [bills[0] / limit, paid[0] / limit,
             sum(bills[:3]) / (3 * limit), sum(paid[:3]) / (3 * limit)]
    return vals
