"""The model: a probability-producing single decision tree."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    # Leaf smoothing through minimum leaf size limits variance on this small sample.
    return DecisionTreeClassifier(max_depth=2, min_samples_leaf=10, random_state=0)
