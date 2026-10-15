"""Random forest classifier for next-month industry relative returns."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    return RandomForestClassifier(n_estimators=300, max_depth=2, min_samples_leaf=100,
                                  max_features=0.7, class_weight=None, random_state=17,
                                  n_jobs=-1)
