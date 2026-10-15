"""Ridge-regularized logistic regression for industry return classification."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Scaling puts the two return horizons on comparable footing; L2 regularization
    # then controls their combined contribution.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, penalty="l2", max_iter=500))
