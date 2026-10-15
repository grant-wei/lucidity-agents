"""The model: a scaled k-nearest-neighbors classifier."""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Uniform neighborhoods provide stable probability estimates for the noisy
    # win-percentage features, rather than overreacting to individual games.
    return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=1200, weights="uniform", p=2))
