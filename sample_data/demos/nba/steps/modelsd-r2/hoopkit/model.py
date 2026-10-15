"""Ridge logistic model implementing the fit/predict_proba contract."""
from sklearn.linear_model import LogisticRegression


def make_model():
    # L2-regularized logistic regression; C=1 is the dev-tuned regularization strength.
    return LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
