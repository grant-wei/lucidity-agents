"""Causally available macro and market signals."""
NAMES = ["hiked_this_month", "yield_3m_minus_target", "yield_2y_minus_target", "yield_10y_minus_target", "yield_curve", "inflation", "unemployment_change_3m"]


def features(months, i):
    """One list of numbers for months[i], in NAMES order, using months[:i + 1] only."""
    m = months[i]
    return [
        float(m["target_change"] > 0),
        m["yield_3m"] - m["target"],
        m["yield_2y"] - m["target"],
        m["yield_10y"] - m["target"],
        m["yield_10y"] - m["yield_3m"],
        m["inflation"],
        m["unemployment_change_3m"],
    ]
