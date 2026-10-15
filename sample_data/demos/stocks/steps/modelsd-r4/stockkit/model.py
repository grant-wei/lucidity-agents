"""Standardized L2-regularized logistic regression (ridge logistic regression)."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    # Heavy L2 shrinkage, selected on the development split to limit noisy signals.
    return make_pipeline(StandardScaler(), LogisticRegression(C=1e-5, solver="lbfgs", max_iter=2000))
