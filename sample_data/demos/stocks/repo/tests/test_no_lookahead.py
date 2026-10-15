"""A month's features may only depend on earlier months."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stockkit import NAMES, examples, load_months  # noqa: E402


def test_features_ignore_the_future():
    months = load_months()[:240]
    cut = 150
    before = examples(months)
    rng = random.Random(0)
    scrambled = [(m, {k: rng.uniform(-20, 20) for k in r}) if i >= cut else (m, dict(r))
                 for i, (m, r) in enumerate(months)]
    after = {(m, ind): f for m, ind, f, _ in examples(scrambled)}
    first = months[cut][0]
    for m, ind, f, _ in before:
        if m <= first and (m, ind) in after:
            assert after[m, ind] == f, f"{ind} in {m}: features changed when later returns did"


def test_one_number_per_name():
    assert all(len(f) == len(NAMES) for _, _, f, _ in examples(load_months()[:24]))
