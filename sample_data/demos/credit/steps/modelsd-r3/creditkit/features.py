"""Non-sensitive account attributes and history-derived inputs."""
MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
BASE_NAMES = (["credit_limit", "education"] + [f"status_{m}" for m in MONTHS]
              + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS])
# Explicit delinquency thresholds let a sparse linear model represent the nonlinear
# risk jump between current accounts and accounts with missed payments.
STATUS_LEVELS = (1, 2, 3, 4, 5, 6, 7, 8)
NAMES = BASE_NAMES + [f"status_{m}_ge_{level}" for m in MONTHS for level in STATUS_LEVELS]


def features(customer):
    """One list of numbers in NAMES order; excludes protected traits and identifiers."""
    base = [customer[name] for name in BASE_NAMES]
    flags = [int(customer[f"status_{m}"] >= level)
             for m in MONTHS for level in STATUS_LEVELS]
    return base + flags
