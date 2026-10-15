"""Boosted-tree model for next-month policy-rate hikes."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Regularized shallow boosting selected using the chronological dev split.
    return GradientBoostingClassifier(
        n_estimators=30,
        learning_rate=0.05,
        max_depth=1,
        min_samples_leaf=5,
        subsample=0.8,
        random_state=0,
    )
