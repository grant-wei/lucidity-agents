"""What the model knows at the end of a month.

A month row has target (the Fed's target rate, or the top of its range since 2008),
target_change (versus last month), end-of-month Treasury yields, and economic indicators
available by month end. hike_next is the answer and must never feed a feature.
"""
NAMES = ["hiked_this_month", "yield_10y", "yield_3m", "yield_2y", "target",
         "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    """Features for months[i], using that month only and never later observations."""
    m = months[i]
    return [float(m["target_change"] > 0), m["yield_10y"], m["yield_3m"], m["yield_2y"],
            m["target"], m["unemployment"], m["unemployment_change_3m"], m["inflation"]]
