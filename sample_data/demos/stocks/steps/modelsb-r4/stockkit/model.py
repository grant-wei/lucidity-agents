"""Scaled linear SVM with training-only probability calibration."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    svm = make_pipeline(StandardScaler(), SVC(kernel="linear", C=100.0))
    return CalibratedClassifierCV(svm, method="sigmoid", cv=5)
