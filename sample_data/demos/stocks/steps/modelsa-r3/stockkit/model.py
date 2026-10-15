"""Scaled distance-weighted k-nearest-neighbor classifier."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

class CalibratedKNN(ClassifierMixin, BaseEstimator):
    """KNN with probabilities shrunk toward the training-set base rate."""
    def __init__(self, n_neighbors=501, shrink=0.10):
        self.n_neighbors, self.shrink = n_neighbors, shrink
    def fit(self, X, y):
        y = np.asarray(y)
        self.model_ = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=self.n_neighbors, weights="distance", p=2))
        self.model_.fit(X, y)
        p = self.model_.predict_proba(X)[:, 1]
        c = p - .5
        den = float(c @ c)
        slope = float(c @ (y - .5) / den) if den else 0.0
        self.slope_ = min(self.shrink, max(0.0, slope))
        self.base_ = float(y.mean())
        self.classes_ = self.model_.classes_
        return self
    def predict_proba(self, X):
        p = self.model_.predict_proba(X)[:, 1]
        q = np.clip(self.base_ + self.slope_ * (p - .5), 1e-6, 1-1e-6)
        return np.column_stack((1-q, q))
def make_model():
    return CalibratedKNN(n_neighbors=501, shrink=0.10)
