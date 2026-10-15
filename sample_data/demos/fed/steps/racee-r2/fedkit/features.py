"""What the model knows at the end of a month; never uses future rows."""
NAMES = ["hiked_this_month", "yield_3m_gap", "yield_2y_gap", "yield_curve", "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    m = months[i]
    return [
        float(m["target_change"] > 0),
        m["yield_3m"] - m["target"],
        m["yield_2y"] - m["target"],
        m["yield_10y"] - m["yield_3m"],
        m["unemployment"],
        m["unemployment_change_3m"],
        m["inflation"],
    ]
