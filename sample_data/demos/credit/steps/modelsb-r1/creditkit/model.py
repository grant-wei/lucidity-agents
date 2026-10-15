"""Scaled support-vector classifier."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    return make_pipeline(StandardScaler(), SVC(C=10.0, kernel="rbf", gamma=0.01,
                                                probability=True, random_state=17))
