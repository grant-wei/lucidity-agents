"""The model: gradient-boosted decision trees."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Conservative trees are important with this small, chronological training set.
    return GradientBoostingClassifier(n_estimators=35, learning_rate=0.03, max_depth=1,
                                     min_samples_leaf=8, subsample=0.8,
                                     max_features=None, random_state=17)
