"""Scaled support-vector classifier with calibrated probabilities."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # A smooth RBF boundary generalizes better than a high-capacity local fit on
    # this small, temporally structured sample.
    return make_pipeline(StandardScaler(), SVC(C=0.1, kernel="rbf", probability=True, random_state=0))
