"""Naive Bayes model for predicting next month's rate increase."""
from sklearn.naive_bayes import GaussianNB


def make_model():
    # GaussianNB handles the binary hike indicator and continuous long yield.
    # A small variance floor prevents near-constant features becoming overconfident.
    return GaussianNB(var_smoothing=1e-3)
