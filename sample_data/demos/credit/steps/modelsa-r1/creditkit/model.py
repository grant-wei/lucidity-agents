"""Scaled k-nearest-neighbors credit-risk model."""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Smooth neighborhood vote; larger neighborhoods reduce high-dimensional variance.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=400, weights="uniform", n_jobs=-1))
