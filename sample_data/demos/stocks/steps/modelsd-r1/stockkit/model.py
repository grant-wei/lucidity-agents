"""Ridge-regularized logistic model."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # L2 penalty (ridge logistic regression); C is inverse regularization strength.
    return LogisticRegression(C=0.1, solver="lbfgs", max_iter=1000)
