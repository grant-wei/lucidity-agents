"""Permitted account-history features; protected traits and identifiers are excluded."""
import math

STATUS_MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
NAMES = ["credit_limit", "education"] + [f"status_{m}_{v}" for m in STATUS_MONTHS for v in (-2, -1, 0, 1, 2, 3)] + [
    f"{kind}_{m}" for kind in ("bill", "paid") for m in STATUS_MONTHS
]


def features(customer):
    """Account variables with repayment status categorical and dollar amounts compressed."""
    out = [customer["credit_limit"], customer["education"]]
    for month in STATUS_MONTHS:
        status = customer[f"status_{month}"]
        out.extend(int(status == value) for value in (-2, -1, 0, 1, 2))
        out.append(int(status >= 3))
    out.extend(math.copysign(math.log1p(abs(customer[f"{kind}_{month}"])), customer[f"{kind}_{month}"]) for kind in ("bill", "paid") for month in STATUS_MONTHS)
    return out
