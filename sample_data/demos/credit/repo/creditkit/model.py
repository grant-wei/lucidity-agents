"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.linear_model import LogisticRegression


def make_model():
    return LogisticRegression()
