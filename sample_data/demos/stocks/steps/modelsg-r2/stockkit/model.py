"""Linear SVM predictor with calibrated probability outputs."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC


def make_model():
    svm = LinearSVC(C=0.001, max_iter=3000, random_state=0)
    calibrated = CalibratedClassifierCV(svm, method="sigmoid", cv=3, ensemble=False)
    return make_pipeline(StandardScaler(), calibrated)
