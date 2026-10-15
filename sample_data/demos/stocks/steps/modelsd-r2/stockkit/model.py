"""Ridge-regularized logistic model."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # Strong L2 regularization keeps the weak return-based signal conservative.
    # C is inverse regularization strength; the small value shrinks probabilities
    # toward the empirical base rate while retaining the logistic ranking.
    return LogisticRegression(C=0.001, solver="lbfgs", max_iter=1000)
