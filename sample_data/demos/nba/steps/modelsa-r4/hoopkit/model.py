"""Plain linear regression classifier with clipped probability predictions."""
import numpy as np
from sklearn.linear_model import LinearRegression


class ClippedLinearRegression:
    """Fit a linear model to binary outcomes and clip its predictions to [1%, 99%]."""
    def __init__(self):
        self.regressor = LinearRegression()

    def fit(self, X, y):
        self.regressor.fit(X, y)
        return self

    def predict_proba(self, X):
        p = np.clip(self.regressor.predict(X), 0.01, 0.99)
        return np.column_stack((1.0 - p, p))


def make_model():
    return ClippedLinearRegression()
