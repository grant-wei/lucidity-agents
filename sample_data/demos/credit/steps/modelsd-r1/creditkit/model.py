"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model():
    # Scaled L2 logistic regression; a modest penalty limits overconfident probabilities.
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.01, penalty="l2", solver="lbfgs", max_iter=2000))
