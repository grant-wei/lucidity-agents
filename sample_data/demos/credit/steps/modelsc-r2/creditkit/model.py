"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # L1 logistic regression on standardized permitted account-history features.
    # A weak penalty retains the useful, correlated history signals.
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(penalty="l1", solver="liblinear", C=1.0, max_iter=5000),
    )
