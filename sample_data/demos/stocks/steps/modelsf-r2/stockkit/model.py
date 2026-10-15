"""Small, regularized boosted-tree classifier for industry outcomes."""
from sklearn.ensemble import GradientBoostingClassifier


class BoostedTrees:
    def __init__(self, max_depth=1, learning_rate=0.01, n_estimators=30, shrink=0.15):
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.shrink = shrink

    def fit(self, X, y):
        self.estimator_ = GradientBoostingClassifier(
            max_depth=self.max_depth, learning_rate=self.learning_rate,
            n_estimators=self.n_estimators, min_samples_leaf=30,
            subsample=0.8, random_state=0,
        ).fit(X, y)
        return self

    def predict_proba(self, X):
        raw = self.estimator_.predict_proba(X)
        return 0.5 + self.shrink * (raw - 0.5)


def make_model():
    return BoostedTrees()
