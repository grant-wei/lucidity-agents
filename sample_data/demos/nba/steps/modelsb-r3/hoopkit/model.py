"""Scaled probabilistic support-vector machine for home-win predictions."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # A smooth RBF boundary uses the Elo matchup signal alongside current-season form.
    return make_pipeline(
        StandardScaler(),
        SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, random_state=0),
    )
