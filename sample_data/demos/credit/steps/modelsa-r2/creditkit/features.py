"""Permitted non-sensitive customer account features."""
BASE = ["credit_limit", "status_sep", "status_aug", "status_jul", "status_jun", "status_may", "status_apr", "bill_sep", "bill_aug", "bill_jul", "bill_jun", "bill_may", "bill_apr", "paid_sep", "paid_aug", "paid_jul", "paid_jun", "paid_may", "paid_apr"]
# Named inputs also include nonlinear basis terms, all derived only from permitted fields.
NAMES = BASE + [f"status_{m}_is_{v}" for m in ("sep", "aug", "jul", "jun", "may", "apr") for v in (-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8)] + [f"history_{m}" for m in ("sep", "aug", "jul", "jun", "may", "apr")] + ["mean_status", "max_status", "late_months", "bill_mean", "bill_latest", "paid_mean", "payment_bill_ratio", "bill_limit_ratio"]


def features(customer):
    """One list of numeric account-history terms, in NAMES order."""
    x = [customer[name] for name in BASE]
    statuses = [customer[f"status_{m}"] for m in ("sep", "aug", "jul", "jun", "may", "apr")]
    bills = [customer[f"bill_{m}"] for m in ("sep", "aug", "jul", "jun", "may", "apr")]
    paid = [customer[f"paid_{m}"] for m in ("sep", "aug", "jul", "jun", "may", "apr")]
    x += [int(s == v) for s in statuses for v in (-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8)]
    x += [s * s for s in statuses]
    limit = max(customer["credit_limit"], 1)
    x += [sum(statuses) / 6, max(statuses), sum(s > 0 for s in statuses), sum(bills) / 6, bills[0], sum(paid) / 6, sum(paid) / (sum(bills) + 1), bills[0] / limit]
    return x
