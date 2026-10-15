"""Ridge-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Scaling allows the L2 penalty to regularize each account variable comparably.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000))
