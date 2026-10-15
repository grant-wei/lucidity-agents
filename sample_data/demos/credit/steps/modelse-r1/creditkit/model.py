"""The model: a scikit-learn-shaped random forest classifier."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=10,
        min_samples_leaf=20,
        max_features=0.8,
        bootstrap=True,
        max_samples=0.8,
        n_jobs=-1,
        random_state=42,
    )
