"""Sex, marital status and age may not feed the decision (US fair-lending rules on protected traits)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creditkit import NAMES, features, load_customers  # noqa: E402

PROTECTED = {"sex": ("male", "female"), "marriage": ("married", "single", "other"), "age": (21, 45, 79)}


def test_features_ignore_protected_traits():
    for c in load_customers()[:500]:
        base = features(c)
        for field, values in PROTECTED.items():
            for v in values:
                assert features({**c, field: v}) == base, f"customer {c['id']}'s features changed with {field}"


def test_no_feature_is_named_for_a_protected_trait():
    assert not [n for n in NAMES if any(p in n.lower() for p in PROTECTED)]


def test_one_number_per_name():
    assert all(len(features(c)) == len(NAMES) for c in load_customers()[:200])
