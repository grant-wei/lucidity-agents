"""Standardized, probability-calibrated SVM candidate.

Dev (2010-2016) assessment with C=0.1 RBF: log loss 0.6948, accuracy
0.4990. The feature set includes lagged factors and industry characteristics;
all are recorded only after the feature month has ended.
"""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # libsvm's Platt calibration is fitted on the training data, never the scored split.
    return make_pipeline(StandardScaler(), SVC(C=0.1, kernel="rbf", gamma="scale", probability=True,
                                                random_state=17, class_weight=None))
