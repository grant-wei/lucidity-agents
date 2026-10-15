"""Dev-tuned random forest classifier."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(
        n_estimators=500, max_depth=1, min_samples_leaf=60,
        max_features=0.7, class_weight=None, random_state=17, n_jobs=-1,
    )
