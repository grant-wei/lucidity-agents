"""Standardized, probability-calibrated RBF SVM candidate.

Dev assessment (2010-2016): RBF SVC C=0.1 produced log loss 0.6948 and
accuracy 0.4990. Features are lagged returns, lagged factors, and industry
characteristics available at feature time; calibration uses training data only.
"""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    return make_pipeline(StandardScaler(), SVC(C=0.1, kernel="rbf", gamma="scale", probability=True,
                                                random_state=17, class_weight=None))
