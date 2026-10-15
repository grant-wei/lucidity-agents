"""Scaled, calibrated SVM classifier."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # A softly regularized linear SVM is robust for this small chronological
    # sample; sigmoid calibration maps its margin to probabilities.
    svm = make_pipeline(StandardScaler(), SVC(C=0.1, kernel="linear", class_weight="balanced"))
    return CalibratedClassifierCV(svm, method="sigmoid", cv=3, ensemble=False)
