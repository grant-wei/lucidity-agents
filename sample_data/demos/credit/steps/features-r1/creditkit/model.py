"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Standardization prevents NT-dollar bill/payment magnitudes swamping repayment status.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000))
