"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Shallow, regularized boosting is a good fit for this small chronological dataset.
    return GradientBoostingClassifier(
        n_estimators=30,
        learning_rate=0.05,
        max_depth=1,
        min_samples_leaf=5,
        subsample=0.8,
        random_state=0,
    )
