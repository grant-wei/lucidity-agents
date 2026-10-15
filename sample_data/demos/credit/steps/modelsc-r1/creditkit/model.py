"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Scale permitted account-history inputs before sparse L1 logistic fitting.
    return make_pipeline(StandardScaler(), LogisticRegression(penalty="l1", solver="liblinear", C=0.2, max_iter=2000))
