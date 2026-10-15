"""What the model knows at the end of a month; never use the answer or future rows."""
NAMES = ["hiked_this_month", "yield_3m_minus_target", "yield_2y_minus_target",
         "yield_10y_minus_target", "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    m = months[i]
    return [float(m["target_change"] > 0), m["yield_3m"] - m["target"],
            m["yield_2y"] - m["target"], m["yield_10y"] - m["target"],
            m["unemployment"], m["unemployment_change_3m"], m["inflation"]]
