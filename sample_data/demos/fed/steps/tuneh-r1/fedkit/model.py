"""The model: a probability-producing single decision tree."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    # Shallow trees keep leaf probabilities reasonably calibrated on this small dataset.
    return DecisionTreeClassifier(max_depth=2, min_samples_leaf=10, random_state=0)
