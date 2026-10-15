"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    return DecisionTreeClassifier(max_depth=3, min_samples_leaf=30, random_state=0)
