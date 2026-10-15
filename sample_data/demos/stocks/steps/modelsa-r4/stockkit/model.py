"""Scaled distance-weighted k-nearest-neighbor classifier."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class CalibratedKNN(ClassifierMixin, BaseEstimator):
    """Distance-weighted KNN, with conservative dev-tuned probability scale."""
    def __init__(self, n_neighbors=51, shrink=0.15):
        self.n_neighbors, self.shrink = n_neighbors, shrink

    def fit(self, X, y):
        y = np.asarray(y)
        self.model_ = make_pipeline(
            StandardScaler(),
            KNeighborsClassifier(n_neighbors=self.n_neighbors, weights="distance", p=2),
        )
        self.model_.fit(X, y)
        # Keep the decision boundary at 0.5; a shifted training prevalence is
        # not a valid calibration estimate for this balanced monthly target.
        self.slope_ = float(self.shrink)
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, X):
        p = self.model_.predict_proba(X)[:, 1]
        q = np.clip(.5 + self.slope_ * (p - .5), 1e-6, 1 - 1e-6)
        return np.column_stack((1 - q, q))


def make_model():
    return CalibratedKNN(n_neighbors=51, shrink=0.15)
