"""What the model knows at the end of a month, never the next month's answer."""
NAMES = ["hiked_this_month", "target", "yield_3m", "yield_2y", "yield_10y", "unemployment", "unemployment_change_3m", "inflation", "short_spread"]


def features(months, i):
    """A row of contemporaneously observed features using months[:i + 1] only."""
    m = months[i]
    return [float(m["target_change"] > 0), m["target"], m["yield_3m"], m["yield_2y"],
            m["yield_10y"], m["unemployment"], m["unemployment_change_3m"], m["inflation"],
            m["yield_2y"] - m["yield_3m"]]
