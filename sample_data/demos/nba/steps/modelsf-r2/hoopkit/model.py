"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    return GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=2,
        min_samples_leaf=20,
        loss="log_loss",
        random_state=0,
    )
