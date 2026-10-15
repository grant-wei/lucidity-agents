"""Features available at the end of each month; never use the answer or future months."""
NAMES = ["hiked_this_month", "target", "yield_3m_minus_target", "yield_2y_minus_target", "yield_10y_minus_target", "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    """One numeric row for months[i], from that month only (reported labor/CPI values lag)."""
    m = months[i]
    target = float(m["target"])
    return [
        float(m["target_change"] > 0), target,
        float(m["yield_3m"]) - target,
        float(m["yield_2y"]) - target,
        float(m["yield_10y"]) - target,
        float(m["unemployment"]), float(m["unemployment_change_3m"]), float(m["inflation"]),
    ]
