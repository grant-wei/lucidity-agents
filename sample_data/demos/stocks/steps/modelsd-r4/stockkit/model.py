"""Ridge-regularized logistic model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Standardization makes the ridge penalty comparable across return horizons.
    return make_pipeline(StandardScaler(), LogisticRegression(C=100.0, solver="lbfgs", max_iter=1000))
