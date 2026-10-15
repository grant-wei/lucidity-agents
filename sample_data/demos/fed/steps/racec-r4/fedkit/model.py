"""Scaled L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # C=0.1 selected by log loss on the chronological 2005-2014 dev split.
    return make_pipeline(StandardScaler(), LogisticRegression(penalty="l1", solver="liblinear", C=0.1,
                                                               max_iter=2000, random_state=0))
