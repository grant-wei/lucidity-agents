"""L1-regularized logistic regression model."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    # Standardization makes the L1 penalty comparable across return lookbacks.
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(solver="liblinear", l1_ratio=1.0, C=0.01, max_iter=2000),
    )
