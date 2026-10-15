"""Scaled probabilistic support-vector machine for home-win predictions."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # A linear margin is less prone to fitting noise in the small annual sample;
    # probability=True fits Platt calibration using training data only.
    return make_pipeline(
        StandardScaler(),
        SVC(kernel="linear", C=0.1, probability=True, random_state=0),
    )
