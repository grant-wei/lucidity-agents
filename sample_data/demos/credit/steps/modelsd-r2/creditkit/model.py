"""The model: scaled L2-regularized logistic regression."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Ridge logistic regression; C selected using development log loss.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, solver="lbfgs", max_iter=3000))
