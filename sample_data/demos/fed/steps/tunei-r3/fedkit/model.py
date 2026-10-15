"""Random forest model for hike probabilities."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    # Larger leaves temper noisy month-to-month probabilities in this small time series.
    return RandomForestClassifier(n_estimators=400, min_samples_leaf=8,
                                  class_weight="balanced_subsample", max_features=1.0,
                                  random_state=42, n_jobs=-1)
