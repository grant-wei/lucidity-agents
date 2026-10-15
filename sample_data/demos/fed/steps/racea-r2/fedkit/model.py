"""Leakage-safe scaled k-nearest-neighbors classifier."""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Tuned on the chronological 2005-2014 development period only.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=25, weights="distance", p=2))
