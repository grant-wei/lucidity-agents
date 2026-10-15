"""Scaled SVM probability model."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # RBF captures nonlinear win-probability relationships. Platt calibration is
    # fitted internally on training data only by libsvm.
    return make_pipeline(
        StandardScaler(),
        SVC(C=0.1, kernel="rbf", gamma="scale", probability=True, random_state=0),
    )
