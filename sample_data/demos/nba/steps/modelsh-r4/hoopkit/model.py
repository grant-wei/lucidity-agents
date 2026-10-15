"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    return DecisionTreeClassifier(max_depth=4, min_samples_leaf=50, random_state=0)
