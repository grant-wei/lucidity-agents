"""The model: a probability-producing single decision tree."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    # A stump's smoothed class rates are deliberately conservative for rare hikes.
    return DecisionTreeClassifier(max_depth=1, min_samples_leaf=15, random_state=0)
