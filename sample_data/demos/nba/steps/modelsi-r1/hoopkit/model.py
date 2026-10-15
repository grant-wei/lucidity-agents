"""Random-forest model for home-win probabilities."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=5,
        min_samples_leaf=35,
        max_features=1.0,
        class_weight=None,
        random_state=17,
        n_jobs=-1,
    )
