"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.tree import DecisionTreeClassifier


def make_model():
    # Small leaves avoid overconfident predictions while allowing nonlinear
    # interactions between each team's pre-game win rate.
    return DecisionTreeClassifier(max_depth=2, min_samples_leaf=100, random_state=0)
