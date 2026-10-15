"""Scaled, calibrated SVM classifier."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Linear SVM with class balancing; sigmoid calibration yields probabilities
    # appropriate for log-loss while retaining a chronological CV calibration.
    svm = make_pipeline(StandardScaler(), SVC(C=0.1, kernel="linear", class_weight="balanced"))
    return CalibratedClassifierCV(svm, method="sigmoid", cv=3, ensemble=False)
