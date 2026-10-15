"""Scaled nearest-neighbor classifier."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier


def make_model():
    # Distance weighting gives nearby policy environments more influence while retaining
    # the local hike frequency as a calibrated probability estimate.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=15, weights="distance", p=2))
