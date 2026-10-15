"""Random-forest probability model."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    # Large leaves regularize the small chronological training sample and keep
    # probabilities useful rather than producing brittle 0/1 estimates.
    return RandomForestClassifier(
        n_estimators=500,
        max_features=1.0,
        min_samples_leaf=8,
        max_depth=3,
        class_weight=None,
        random_state=17,
        n_jobs=-1,
    )
