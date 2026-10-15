"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def make_model():
    # Scaling is essential for meaningful kernel distances; probability=True enables
    # the calibrated probabilities consumed by the scoring script.
    return make_pipeline(StandardScaler(), SVC(C=1.0, kernel="rbf", probability=True, random_state=0))
