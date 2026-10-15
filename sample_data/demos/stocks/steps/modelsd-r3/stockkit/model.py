"""L1-regularized (lasso) logistic classifier."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # L1 selects the most useful features while keeping a linear probability model.
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(penalty="l1", solver="liblinear", C=0.01, max_iter=500),
    )
