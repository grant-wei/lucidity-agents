"""What the model knows at the end of a month, using no future observations."""
NAMES = ["hiked_this_month", "bill_minus_target", "two_year_minus_target", "ten_year_minus_target",
         "yield_curve", "inflation", "unemployment_change_3m"]


def features(months, i):
    """One list of numbers for months[i], in NAMES order, using months[:i + 1] only."""
    m = months[i]
    target = m["target"]
    return [float(m["target_change"] > 0), m["yield_3m"] - target,
            m["yield_2y"] - target, m["yield_10y"] - target,
            m["yield_10y"] - m["yield_3m"], m["inflation"], m["unemployment_change_3m"]]
