"""The model: a scaled k-nearest-neighbors classifier."""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # A fairly broad neighborhood smooths noisy sequential team-strength estimates.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=800, weights="uniform", p=2))
