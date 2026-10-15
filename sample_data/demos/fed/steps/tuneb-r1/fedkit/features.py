"""What the model knows at the end of a month.

A month row has target (the Fed's target rate, or the top of its range since 2008),
target_change (versus last month), end-of-month Treasury yields (yield_3m, yield_2y,
yield_10y), and last month's unemployment, unemployment_change_3m and inflation
(CPI, year over year). hike_next is the answer and must never feed a feature.
"""
NAMES = ["target", "target_change", "yield_3m", "yield_2y", "yield_10y",
         "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    """One list of numbers for months[i], using months[:i + 1] only."""
    m = months[i]
    return [float(m[name]) for name in NAMES]
