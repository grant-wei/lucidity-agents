TO_METRIC = {'cup': ('ml', 236.6), 'tbsp': ('ml', 14.8), 'oz': ('g', 28.35)}


def to_metric(qty, unit):
    name, factor = TO_METRIC[unit]
    return round(qty * factor, 1), name
