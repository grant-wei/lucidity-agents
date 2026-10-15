"""Scaled linear support-vector classifier with probability calibration."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC


class ScaledSVM:
    """Linear SVM with logistic calibration of its decision scores."""
    def __init__(self):
        self.scaler = StandardScaler()
        self.svm = LinearSVC(C=0.03, class_weight=None, dual="auto", max_iter=3000,
                             random_state=17)
        self.calibrator = LogisticRegression(C=1000.0, random_state=17)

    def fit(self, X, y):
        X = self.scaler.fit_transform(X)
        self.svm.fit(X, y)
        self.calibrator.fit(self.svm.decision_function(X).reshape(-1, 1), y)
        return self

    def predict_proba(self, X):
        scores = self.svm.decision_function(self.scaler.transform(X)).reshape(-1, 1)
        return self.calibrator.predict_proba(scores)


def make_model():
    return ScaledSVM()
