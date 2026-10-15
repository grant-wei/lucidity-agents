"""The model: gradient-boosted decision trees."""
from sklearn.ensemble import GradientBoostingClassifier


def make_model():
    # Shallow regularized trees provide nonlinearities while limiting variance.
    return GradientBoostingClassifier(n_estimators=45, learning_rate=0.035, max_depth=2,
                                      min_samples_leaf=10, min_samples_split=20,
                                      subsample=0.8, max_features=None, random_state=17,
                                      loss="log_loss")
