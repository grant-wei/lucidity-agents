from .streak import current_streak


def longest_streak(days):
    first, *rest = days
    return current_streak(days)
