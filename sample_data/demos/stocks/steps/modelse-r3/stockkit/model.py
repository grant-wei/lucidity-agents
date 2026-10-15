"""Dev-tuned random forest classifier."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(
        n_estimators=800, max_depth=1, min_samples_leaf=25,
        max_features=1.0, class_weight=None, random_state=17, n_jobs=-1,
    )
