"""Standardized L2-regularized logistic regression (ridge logistic regression)."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    # Strong shrinkage reduces noisy coefficients; selected on the 2010-2016 dev split.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.001, solver="lbfgs", max_iter=2000))
