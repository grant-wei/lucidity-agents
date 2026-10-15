"""Plain least-squares regression used as a probability predictor."""
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

class ClippedLinearRegression:
    """Ordinary linear regression with outputs clipped to probability bounds."""
    def __init__(self):
        self.scaler = StandardScaler()
        self.regression = LinearRegression()

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        self.regression.fit(self.scaler.fit_transform(X), y)
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        p = np.clip(self.regression.predict(self.scaler.transform(X)), 0.01, 0.99)
        return np.column_stack((1.0 - p, p))

def make_model():
    return ClippedLinearRegression()
