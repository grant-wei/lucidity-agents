"""The model: a probability-producing single decision tree."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    # A shallow tree limits variance while retaining useful rate-regime splits.
    return DecisionTreeClassifier(max_depth=2, min_samples_leaf=8, random_state=0)
