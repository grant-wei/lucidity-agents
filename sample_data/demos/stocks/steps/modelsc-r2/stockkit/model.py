"""Naive Bayes model for monthly industry outcomes."""
from sklearn.naive_bayes import GaussianNB


def make_model():
    # A modest variance floor prevents a small number of extreme return observations
    # from producing overconfident class likelihoods.
    return GaussianNB(var_smoothing=0.1)
