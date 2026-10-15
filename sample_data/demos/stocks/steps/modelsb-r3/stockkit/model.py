"""Fast standardized RBF SVM with a sigmoid probability mapping.

SVC's built-in probability=True performs an internal five-fold calibration, which
is prohibitively slow on the full time-series training set. This wrapper maps the
SVM margin to probabilities directly; the mapping is intentionally conservative.
"""
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


class MarginProbabilities:
    """Expose an SVM decision margin through the predict_proba interface."""
    classes_ = np.array([0, 1])

    def __init__(self, estimator, temperature=2.0):
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
    svm = make_pipeline(StandardScaler(), SVC(C=0.1, kernel="rbf", gamma="scale",
                                               probability=False, random_state=17))
    return MarginProbabilities(svm, temperature=2.0)
