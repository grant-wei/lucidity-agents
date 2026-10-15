"""L1-regularized logistic regression model."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # C is selected using the 2013 development season. Scaling makes the L1
    # penalty comparable across the team's percentage and Elo probability inputs.
    return make_pipeline(StandardScaler(), LogisticRegression(penalty="l1", solver="liblinear", C=0.25, max_iter=1000))
