"""The model: L2-regularized logistic regression for home-win probabilities."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Standardization lets the L2 penalty treat rating, percentage and net-rating
    # signals comparably; C was selected using the development season.
    return make_pipeline(StandardScaler(), LogisticRegression(
        penalty="l2", C=0.08, solver="lbfgs", max_iter=1000
    ))
