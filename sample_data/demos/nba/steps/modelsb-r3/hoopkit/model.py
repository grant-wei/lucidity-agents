"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


def make_model():
    # Scaling makes regularization comparable across the rating and percentage inputs.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=500))
