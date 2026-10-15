"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(l1_ratio=1.0, solver="liblinear", C=1.0, max_iter=2000),
    )
