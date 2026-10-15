"""Scaled support-vector classifier with calibrated probabilities."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Low regularization gives a smooth boundary on the small, temporally held-out sample.
    return make_pipeline(StandardScaler(), SVC(C=0.03, kernel="rbf", gamma="scale", probability=True, random_state=0))
