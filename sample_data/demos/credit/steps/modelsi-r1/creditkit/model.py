"""Random forest model for next-month delinquency risk."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(
        n_estimators=500,
        max_features=0.7,
        min_samples_leaf=30,
        max_depth=12,
        class_weight=None,
        random_state=42,
        n_jobs=-1,
    )
