"""Scaled, calibrated SVM classifier."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # RBF SVM with sigmoid calibration gives stable probabilities on the small,
    # imbalanced chronological training sample.
    svm = make_pipeline(StandardScaler(), SVC(C=0.1, kernel="linear", class_weight="balanced"))
    return CalibratedClassifierCV(svm, method="sigmoid", cv=3, ensemble=False)
