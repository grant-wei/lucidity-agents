"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Dev-selected C; the standardized inputs make the L1 penalty comparable.
    return make_pipeline(StandardScaler(), LogisticRegression(penalty="l1", solver="liblinear", C=0.12, max_iter=1000))
