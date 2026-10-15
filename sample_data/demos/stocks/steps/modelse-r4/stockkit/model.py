"""Random-forest probability model for next-month industry outcomes."""
from sklearn.ensemble import RandomForestClassifier


class CalibratedForest(RandomForestClassifier):
    """Shrink noisy forest probabilities toward the balanced prior."""
    def predict_proba(self, X):
        p = super().predict_proba(X)
        p[:, 1] = 0.5 + 0.05 * (p[:, 1] - 0.5)
        p[:, 0] = 1.0 - p[:, 1]
        return p


def make_model():
    return CalibratedForest(
        n_estimators=500,
        max_depth=1,
        min_samples_leaf=100,
        max_features=1.0,
        random_state=17,
        n_jobs=-1,
    )
