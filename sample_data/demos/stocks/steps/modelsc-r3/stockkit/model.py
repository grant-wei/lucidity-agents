"""Naive Bayes model for monthly industry outcomes."""
from sklearn.naive_bayes import GaussianNB


def make_model():
    # Strong smoothing makes Gaussian likelihoods conservative in the presence of
    # heavy-tailed monthly returns; it was selected against the dev split.
    return GaussianNB(var_smoothing=0.1)
