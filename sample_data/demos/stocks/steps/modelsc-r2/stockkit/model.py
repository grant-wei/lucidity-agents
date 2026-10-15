"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # L1 shrinkage with regularization selected using the development period.
    return LogisticRegression(solver="liblinear", l1_ratio=1.0, C=100.0, max_iter=2000)
