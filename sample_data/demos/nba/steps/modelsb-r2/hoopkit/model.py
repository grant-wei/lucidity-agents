"""Scaled probabilistic support-vector machine for home-win predictions."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Linear SVM avoids the overfitting seen with an RBF kernel on the two
    # noisy, correlated win-percentage features.
    return make_pipeline(
        StandardScaler(),
        SVC(kernel="linear", C=0.01, probability=True, random_state=0),
    )
