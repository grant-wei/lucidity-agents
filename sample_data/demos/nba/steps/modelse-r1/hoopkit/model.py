"""The model: L2-regularized logistic regression for home-win probabilities."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # C controls inverse L2 regularization strength; selected on the dev split.
    return LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=1000)
