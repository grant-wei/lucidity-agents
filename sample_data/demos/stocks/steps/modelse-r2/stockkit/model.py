"""Random-forest probability model for next-month industry outcomes."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    # Strongly regularized trees limit probability overconfidence on noisy returns.
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=1,
        min_samples_leaf=100,
        max_features=1.0,
        random_state=17,
        n_jobs=-1,
    )
