def current_streak(days):
    streak = 1
    for a, b in zip(days, days[1:]):
        streak = streak + 1 if (b - a).days == 1 else 1
    return streak
