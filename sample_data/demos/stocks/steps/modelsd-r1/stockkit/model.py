"""Standardized L2-regularized logistic regression."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    # Moderate ridge shrinkage, selected using the development period.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, solver="lbfgs", max_iter=2000))
