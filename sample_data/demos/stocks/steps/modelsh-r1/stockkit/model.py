"""A conservatively pruned single decision tree classifier."""
from sklearn.tree import DecisionTreeClassifier


class PrunedTree:
    def __init__(self):
        self.tree = DecisionTreeClassifier(max_depth=1, min_samples_leaf=400,
                                           ccp_alpha=0.0, random_state=0)

    def fit(self, x, y):
        self.tree.fit(x, y)
        return self

    def predict_proba(self, x):
        return self.tree.predict_proba(x)


def make_model():
    return PrunedTree()
