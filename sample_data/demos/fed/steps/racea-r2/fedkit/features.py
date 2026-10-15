"""What the model knows at the end of a month; never includes the next month's answer."""
NAMES = ["hiked_this_month", "target", "yield_3m_gap", "yield_2y_gap", "yield_10y_gap",
         "inflation", "unemployment", "unemployment_change_3m"]


def features(months, i):
    m = months[i]
    return [float(m["target_change"] > 0), m["target"], m["yield_3m"] - m["target"],
            m["yield_2y"] - m["target"], m["yield_10y"] - m["target"], m["inflation"],
            m["unemployment"], m["unemployment_change_3m"]]
