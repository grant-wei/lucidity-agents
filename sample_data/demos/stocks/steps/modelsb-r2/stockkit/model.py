"""Plain logistic regression candidate."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000, solver="lbfgs"))
