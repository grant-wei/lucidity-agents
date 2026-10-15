"""Standardized linear SVM with a conservative sigmoid margin mapping."""
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


class MarginProbabilities:
    """Expose the SVM decision margin through the predict_proba interface."""
    classes_ = np.array([0, 1])

    def __init__(self, estimator, temperature=1.0):
        self.estimator = estimator
        self.temperature = temperature

    def fit(self, X, y):
        self.estimator.fit(X, y)
        return self

    def predict_proba(self, X):
        margin = np.clip(self.estimator.decision_function(X) / self.temperature, -30, 30)
        p = 1.0 / (1.0 + np.exp(-margin))
        return np.column_stack((1.0 - p, p))


def make_model():
    svm = make_pipeline(StandardScaler(), SVC(C=0.01, kernel="linear", probability=False,
                                               random_state=17))
    return MarginProbabilities(svm, temperature=10.0)
