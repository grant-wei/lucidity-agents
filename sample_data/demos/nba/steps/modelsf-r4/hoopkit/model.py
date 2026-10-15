"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Tuned on the 2013 development season; keep the prediction family boosted trees.
    return GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=2,
        min_samples_leaf=30,
        loss="log_loss",
        random_state=0,
    )
