"""L1-regularized logistic regression for pregame win probabilities."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # C is selected on the development season; smaller values impose stronger sparsity.
    return LogisticRegression(penalty="l1", solver="liblinear", C=0.1, max_iter=1000)
