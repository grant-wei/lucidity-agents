"""Scaled k-nearest-neighbor model for industry-month observations."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier


def make_model():
    # Broad uniform neighborhood reduces noisy probabilities on the limited industry panel.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=200, weights="uniform"))
