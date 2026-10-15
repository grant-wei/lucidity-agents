"""L1-regularized logistic regression for pregame win probabilities."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # Tuned on the development season. L1 keeps this a sparse logistic model;
    # a weaker penalty than the initial setting preserves useful margin signal.
    return LogisticRegression(penalty="l1", solver="liblinear", C=1.0, max_iter=1000)
