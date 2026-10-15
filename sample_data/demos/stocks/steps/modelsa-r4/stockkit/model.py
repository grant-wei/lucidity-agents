"""A prior-smoothed k-nearest-neighbors classifier."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


class SmoothedKNNClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, n_neighbors=5, smoothing=10000.0, weights="uniform"):
        self.n_neighbors = n_neighbors
        self.smoothing = smoothing
        self.weights = weights

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.prior_ = float(np.mean(y))
        self.scaler_ = StandardScaler().fit(X)
        self.nn_ = NearestNeighbors(n_neighbors=min(self.n_neighbors, len(X))).fit(self.scaler_.transform(X))
        self.y_ = np.asarray(y, dtype=float)
        return self

    def predict_proba(self, X):
        d, ix = self.nn_.kneighbors(self.scaler_.transform(X))
        w = 1.0 / np.maximum(d, 1e-6) if self.weights == "distance" else np.ones_like(d)
        successes, total = (w * self.y_[ix]).sum(axis=1), w.sum(axis=1)
        p = (successes + self.smoothing * self.prior_) / (total + self.smoothing)
        return np.column_stack((1.0 - p, p))


def make_model():
    return SmoothedKNNClassifier()
