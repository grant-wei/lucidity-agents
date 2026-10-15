"""Scaled L2-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


# C selected by chronological dev-split experiments (smaller C means stronger ridge penalty).
REGULARIZATION_C = 1.0


def make_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=REGULARIZATION_C, penalty="l2", max_iter=2000))
