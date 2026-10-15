"""Scaled probabilistic support-vector machine for home-win predictions."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # RBF kernel and regularization selected on the development season.
    return make_pipeline(
        StandardScaler(),
        SVC(kernel="rbf", C=0.1, gamma="scale", probability=True, random_state=0),
    )
