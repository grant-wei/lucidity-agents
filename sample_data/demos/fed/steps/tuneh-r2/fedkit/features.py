"""What the model knows at the end of a month.

Features use only contemporaneous observations and prior-month changes; hike_next is never used.
"""
NAMES = ["hiked_this_month", "yield_3m", "yield_2y", "yield_10y", "unemployment",
         "unemployment_change_3m", "inflation", "target"]


def features(months, i):
    """One list of numbers for months[i], in NAMES order, using months[:i + 1] only."""
    m = months[i]
    return [float(m["target_change"] > 0), m["yield_3m"], m["yield_2y"], m["yield_10y"],
            m["unemployment"], m["unemployment_change_3m"], m["inflation"], m["target"]]
