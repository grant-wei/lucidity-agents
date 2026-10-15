"""SVM classifier with calibrated probability outputs."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Calibrate the RBF support-vector classifier to produce log-loss-ready probabilities.
    return make_pipeline(StandardScaler(), CalibratedClassifierCV(SVC(C=3, kernel="rbf", gamma="scale"), cv=3, method="sigmoid"))
