"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # Returns are in percentage points; C controls the strength of L1 shrinkage.
    return LogisticRegression(solver="liblinear", l1_ratio=1.0, C=10.0, max_iter=2000)
