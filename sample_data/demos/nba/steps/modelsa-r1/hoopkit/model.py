"""Scaled k-nearest-neighbors forecast with conservative probability calibration."""
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler


class ScaledKNN:
    def __init__(self, n_neighbors=300, weights="uniform", shrink=0.01):
        self.n_neighbors, self.weights, self.shrink = n_neighbors, weights, shrink

    def fit(self, X, y):
        self.scaler = StandardScaler().fit(X)
        self.knn = KNeighborsClassifier(n_neighbors=self.n_neighbors, weights=self.weights)
        self.knn.fit(self.scaler.transform(X), y)
        self.prior = float(np.mean(y))
        return self

    def predict_proba(self, X):
        raw = self.knn.predict_proba(self.scaler.transform(X))[:, 1]
        p = self.prior + (raw - self.prior) * self.shrink
        return np.column_stack((1 - p, p))


def make_model():
    return ScaledKNN()
