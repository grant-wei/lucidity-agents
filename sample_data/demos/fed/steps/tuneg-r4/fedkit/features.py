"""What the model knows at the end of a month; never use future observations."""
NAMES = ["hiked_this_month", "target", "yield_3m_minus_target", "yield_2y_minus_target",
         "yield_10y_minus_target", "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    m = months[i]
    target = m["target"]
    return [float(m["target_change"] > 0), target, m["yield_3m"] - target,
            m["yield_2y"] - target, m["yield_10y"] - target,
            m["unemployment"], m["unemployment_change_3m"], m["inflation"]]
