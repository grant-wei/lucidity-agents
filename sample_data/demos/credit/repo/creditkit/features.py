"""What the model knows about a customer: their account as of September 2005.

A customer row has credit_limit, education, six months of repayment status (status_sep back to
status_apr: -2 no balance, -1 paid in full, 0 revolving, 1-9 months late), bills (bill_*) and
payments (paid_*) in NT dollars. It also has sex, marriage and age, which lending rules keep out of
the decision: tests/test_fair_lending.py fails if a feature uses them.
"""
NAMES = ["credit_limit", "status_sep"]


def features(customer):
    """One list of numbers, in NAMES order."""
    return [customer["credit_limit"], customer["status_sep"]]
