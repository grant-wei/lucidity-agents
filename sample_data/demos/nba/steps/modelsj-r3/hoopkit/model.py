"""A regularized boosted-tree classifier for pregame outcomes."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    return GradientBoostingClassifier(
        n_estimators=60, learning_rate=0.025, max_depth=1,
        min_samples_leaf=35, loss="log_loss", random_state=0,
    )
