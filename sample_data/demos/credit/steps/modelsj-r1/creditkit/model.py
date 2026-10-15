"""Boosted-tree model for default risk."""
from sklearn.ensemble import HistGradientBoostingClassifier


def make_model():
    return HistGradientBoostingClassifier(
        max_iter=250, learning_rate=0.04, max_leaf_nodes=7,
        l2_regularization=5.0, min_samples_leaf=40, random_state=0,
    )
