"""Random forest classifier for next-month industry relative returns."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    # Small leaves retain modest nonlinearities while bootstrap averaging regularizes probabilities.
    return RandomForestClassifier(n_estimators=500, max_depth=1, min_samples_leaf=80,
                                  max_features=0.75, bootstrap=True, max_samples=0.8,
                                  class_weight=None, random_state=17, n_jobs=-1)
