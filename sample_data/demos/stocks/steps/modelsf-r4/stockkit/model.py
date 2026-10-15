"""Gradient-boosted tree candidate tuned on the 2010-2016 dev split."""
from sklearn.ensemble import HistGradientBoostingClassifier


def make_model():
    # Conservative dev-selected configuration avoids overfitting noisy monthly labels.
    return HistGradientBoostingClassifier(
        max_iter=80,
        learning_rate=0.01,
        max_leaf_nodes=8,
        min_samples_leaf=100,
        l2_regularization=5.0,
        early_stopping=False,
        random_state=7,
    )
