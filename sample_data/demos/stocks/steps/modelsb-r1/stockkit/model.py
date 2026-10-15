"""SVM classifier with scaled inputs and training-only probability calibration."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Linear decision boundary is deliberately regularized; calibration is performed
    # by stratified folds drawn exclusively from the supplied training observations.
    svm = make_pipeline(StandardScaler(), SVC(kernel="linear", C=0.01))
    return CalibratedClassifierCV(svm, method="sigmoid", cv=5)
