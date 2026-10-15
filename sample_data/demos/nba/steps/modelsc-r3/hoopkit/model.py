"""L1-regularized logistic regression for pregame win probabilities."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # L1 logistic regression; regularization strength tuned on the dev season.
    return LogisticRegression(solver="liblinear", C=0.3, max_iter=1000)
