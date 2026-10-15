"""Standardized L1-penalized logistic regression."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(solver="liblinear", l1_ratio=1, C=0.003,
                           max_iter=3000, random_state=0),
    )
