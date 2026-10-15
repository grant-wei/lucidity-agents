"""Dev-calibrated, scaled distance-weighted k-nearest-neighbor classifier."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class CalibratedKNN(ClassifierMixin, BaseEstimator):
    """KNN with conservative probability calibration fitted exclusively on training data."""
    def __init__(self, n_neighbors=501, shrink=0.10):
        self.n_neighbors = n_neighbors
        self.shrink = shrink

    def fit(self, X, y):
        self.model_ = make_pipeline(StandardScaler(), KNeighborsClassifier(
            n_neighbors=self.n_neighbors, weights="distance", p=2))
        self.model_.fit(X, y)
        p = self.model_.predict_proba(X)[:, 1]
        # A strongly regularized calibration slope avoids overconfident probabilities.
        centered = p - .5
        denom = float(np.dot(centered, centered))
        slope = float(np.dot(centered, np.asarray(y) - .5) / denom) if denom else 0.0
        self.slope_ = min(self.shrink, max(0.0, slope))
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, X):
        p = self.model_.predict_proba(X)[:, 1]
        q = np.clip(.5 + self.slope_ * (p - .5), 1e-6, 1 - 1e-6)
        return np.column_stack((1 - q, q))


def make_model():
    return CalibratedKNN(n_neighbors=501, shrink=0.10)
