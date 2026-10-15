"""Scaled SVM classifier with probability calibration."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    return make_pipeline(StandardScaler(), SVC(C=1.0, kernel="rbf", gamma="scale", probability=True, random_state=17))
