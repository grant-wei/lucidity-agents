"""Scaled k-nearest-neighbor probability model."""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Uniform neighborhoods avoid overly confident inverse-distance estimates.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(
        n_neighbors=500, weights="uniform", p=2, n_jobs=-1))
