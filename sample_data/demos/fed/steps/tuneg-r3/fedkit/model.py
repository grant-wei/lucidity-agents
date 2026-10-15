"""Scaled support-vector classifier with calibrated probabilities."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # A smooth RBF boundary generalizes well on this small temporal sample.
    return make_pipeline(StandardScaler(), SVC(C=0.1, kernel="rbf", gamma="scale", probability=True, random_state=0))
