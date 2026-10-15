"""What the model knows at the end of a month.

A month row has target (the Fed's target rate, or the top of its range since 2008), target_change
(versus last month), end-of-month Treasury yields (yield_3m, yield_2y, yield_10y), and last month's
unemployment, unemployment_change_3m and inflation (CPI, year over year), all in percent. hike_next
is the answer and must never feed a feature. tests/test_no_lookahead.py fails if a feature reads a
later month.
"""
NAMES = ["hiked_this_month", "yield_10y"]


def features(months, i):
    """One list of numbers for months[i], in NAMES order, using months[:i + 1] only."""
    m = months[i]
    return [float(m["target_change"] > 0), m["yield_10y"]]
