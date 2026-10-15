"""What the model knows at the end of a month (never the future or target)."""
NAMES = ["hiked_this_month", "yield_3m_minus_target", "yield_2y_minus_target", "yield_10y_minus_target", "unemployment", "unemployment_change_3m", "inflation", "yield_curve_10y_3m"]


def features(months, i):
    """Contemporaneously known macro and market indicators."""
    m = months[i]
    return [float(m["target_change"] > 0), m["yield_3m"] - m["target"],
            m["yield_2y"] - m["target"], m["yield_10y"] - m["target"],
            m["unemployment"], m["unemployment_change_3m"], m["inflation"],
            m["yield_10y"] - m["yield_3m"]]
