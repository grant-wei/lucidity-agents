"""Scaled nearest-neighbor classifier."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier


def make_model():
    # Small neighborhood selected on the dev split; distance weighting smooths the
    # local hike frequency without discarding nearby observations.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=7, weights="distance", p=2))
