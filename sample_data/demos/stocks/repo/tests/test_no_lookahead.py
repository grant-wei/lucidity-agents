"""A month's features may only depend on earlier months."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stockkit import NAMES, examples, load_info, load_months  # noqa: E402


def test_features_ignore_the_future():
    months, info = load_months()[:240], load_info()
    cut = 150
    before = examples(months, info)
    rng = random.Random(0)
    scrambled = [(m, {k: rng.uniform(-20, 20) for k in r}) if i >= cut else (m, dict(r))
                 for i, (m, r) in enumerate(months)]
    late = {m for m, _ in months[cut:]}
    noise = {m: {"factors": {k: rng.uniform(-20, 20) for k in d["factors"]},
                 "industries": {i: {"firms": rng.randint(1, 500), "size": rng.uniform(1, 1e5), "be_me": rng.uniform(0, 3)}
                                for i in d["industries"]}} if m in late else d for m, d in info.items()}
    after = {(m, ind): f for m, ind, f, _ in examples(scrambled, noise)}
    first = months[cut][0]
    for m, ind, f, _ in before:
        if m <= first and (m, ind) in after:
            assert after[m, ind] == f, f"{ind} in {m}: features changed when later returns did"


def test_one_number_per_name():
    assert all(len(f) == len(NAMES) for _, _, f, _ in examples(load_months()[:24]))
