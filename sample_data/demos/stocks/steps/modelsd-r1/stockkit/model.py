"""L1-regularized (lasso) logistic classifier."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Scaling is essential for a meaningful L1 penalty across return horizons.
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(penalty="l1", solver="liblinear", C=0.03, max_iter=500),
    )
