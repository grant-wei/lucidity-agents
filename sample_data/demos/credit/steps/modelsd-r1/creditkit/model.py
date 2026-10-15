"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Scaling is essential for a meaningful shared L1 penalty across monetary/status columns.
    return make_pipeline(StandardScaler(), LogisticRegression(
        l1_ratio=1.0, C=0.01, solver="liblinear", max_iter=1000
    ))
