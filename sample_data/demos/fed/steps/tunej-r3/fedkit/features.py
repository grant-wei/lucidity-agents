"""What the model knows at the end of a month; no future outcomes are used."""
NAMES = ["hiked_this_month", "target", "yield_3m", "yield_2y", "yield_10y", "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    """One list of contemporaneously available predictors for months[i]."""
    m = months[i]
    return [float(m["target_change"] > 0), m["target"], m["yield_3m"], m["yield_2y"], m["yield_10y"], m["unemployment"], m["unemployment_change_3m"], m["inflation"]]
