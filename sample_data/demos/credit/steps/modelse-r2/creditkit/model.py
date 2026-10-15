"""Ridge-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # L2 regularization on standardized permitted account-history features.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=1000))
