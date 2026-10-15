"""L1-regularized logistic regression for pregame win probabilities."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # L1 logistic regression; regularization strength selected using the dev season.
    return LogisticRegression(solver="liblinear", l1_ratio=1.0, C=0.3, max_iter=2000)
