"""A month's features may only use that month and earlier ones: the future can't leak in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fedkit import NAMES, features, load_months  # noqa: E402


def scramble(m):
    return {k: v if k == "month" else (1 - v if k == "hike_next" else v * 3 + 7) for k, v in m.items()}


def test_features_ignore_later_months():
    months = load_months()
    for i in range(0, len(months) - 1, 7):
        changed = months[:i + 1] + [scramble(m) for m in months[i + 1:]]
        assert features(changed, i) == features(months, i), f"{months[i]['month']} reads a later month"


def test_features_ignore_this_months_answer():
    months = load_months()
    for i in range(0, len(months), 11):
        flipped = months[:i] + [{**months[i], "hike_next": 1 - months[i]["hike_next"]}] + months[i + 1:]
        assert features(flipped, i) == features(months, i), f"{months[i]['month']} reads hike_next"


def test_one_number_per_name():
    months = load_months()
    assert all(len(features(months, i)) == len(NAMES) for i in range(len(months)))
