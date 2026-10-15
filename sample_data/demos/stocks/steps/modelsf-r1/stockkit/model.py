"""Conservative gradient-boosted tree candidate."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Shallow trees and a modest learning rate limit overfit on noisy monthly labels.
    return GradientBoostingClassifier(n_estimators=80, learning_rate=0.03, max_depth=2,
                                      min_samples_leaf=80, subsample=0.8, random_state=7)
