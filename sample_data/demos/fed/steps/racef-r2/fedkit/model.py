"""The model: gradient-boosted decision trees."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Shallow, regularized trees avoid memorizing individual months in this small sample.
    return GradientBoostingClassifier(n_estimators=30, learning_rate=0.04, max_depth=1,
                                      min_samples_leaf=10, subsample=0.8,
                                      max_features=None, random_state=17)
