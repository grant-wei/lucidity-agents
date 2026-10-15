"""SVM classifier with scaled inputs and training-only probability calibration."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Strongly regularized linear SVM avoids overfitting this weak two-feature signal.
    # The calibrator uses stratified folds from the supplied fit data only.
    svm = make_pipeline(StandardScaler(), SVC(kernel="linear", C=0.01))
    return CalibratedClassifierCV(svm, method="sigmoid", cv=5)
