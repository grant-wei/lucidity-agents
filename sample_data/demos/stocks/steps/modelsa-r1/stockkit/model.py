"""Scaled, distance-weighted k-nearest-neighbor classifier."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier


def make_model():
    # Broad neighborhood limits variance in the noisy cross-industry monthly labels.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=501, weights="distance", p=2))
