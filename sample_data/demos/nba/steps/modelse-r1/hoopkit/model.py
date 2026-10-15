"""The model: anything scikit-learn-shaped with fit() and predict_proba()."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    # A moderate ensemble of shallow trees regularizes noisy win percentages.
    return RandomForestClassifier(
        n_estimators=400,
        max_depth=3,
        min_samples_leaf=20,
        max_features=1.0,
        random_state=17,
        n_jobs=-1,
    )
