"""Gradient-boosted tree model."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    return GradientBoostingClassifier(n_estimators=30, learning_rate=0.02, max_depth=1,
                                      min_samples_leaf=100, subsample=0.8, random_state=17)
