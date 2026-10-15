"""Naive Bayes model for predicting next month's rate increase."""
from sklearn.naive_bayes import GaussianNB


def make_model():
    # A small variance floor prevents nearly constant features becoming overconfident.
    return GaussianNB(var_smoothing=1e-3)
