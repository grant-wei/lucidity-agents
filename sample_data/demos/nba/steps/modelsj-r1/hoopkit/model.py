"""The model: a deliberately shallow boosted-tree classifier."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Restrained trees reduce variance on the two available pregame features.
    return GradientBoostingClassifier(
        n_estimators=25, learning_rate=0.03, max_depth=2,
        min_samples_leaf=40, loss="log_loss", random_state=0,
    )
