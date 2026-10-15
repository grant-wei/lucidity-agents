"""Ridge-regularized logistic model."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # L2-regularized logistic regression; C is inverse penalty strength.
    return LogisticRegression(C=10.0, solver="lbfgs", max_iter=1000)
