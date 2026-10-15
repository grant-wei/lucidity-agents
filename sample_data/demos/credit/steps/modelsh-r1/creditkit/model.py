"""Single decision tree candidate."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    return DecisionTreeClassifier(max_depth=4, min_samples_leaf=500, random_state=0, criterion="log_loss")
