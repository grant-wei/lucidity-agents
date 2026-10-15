"""Random forest model with probability output."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(n_estimators=500, max_depth=4, min_samples_leaf=35,
                                  max_features=1.0, random_state=17, n_jobs=-1)
