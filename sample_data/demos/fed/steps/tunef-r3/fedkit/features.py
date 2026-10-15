"""What the model knows at the end of a month; never reads future rows."""
NAMES = ["target", "target_change", "yield_3m", "yield_2y", "yield_10y", "unemployment", "unemployment_change_3m", "inflation"]


def features(months, i):
    """Return contemporaneously available indicators for this month."""
    m = months[i]
    return [float(m[name]) for name in NAMES]
