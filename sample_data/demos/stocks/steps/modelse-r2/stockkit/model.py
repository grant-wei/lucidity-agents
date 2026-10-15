"""Ridge-regularized logistic regression for industry return classification."""
from sklearn.linear_model import LogisticRegression


def make_model():
    return LogisticRegression(C=1.0, penalty="l2", max_iter=500)
