"""Conservative gradient-boosted tree candidate."""
from sklearn.ensemble import HistGradientBoostingClassifier


def make_model():
    # Regularized shallow boosting; early stopping prevents fitting noisy monthly labels.
    return HistGradientBoostingClassifier(max_iter=60, learning_rate=0.025, max_leaf_nodes=5,
                                         min_samples_leaf=100, l2_regularization=5.0,
                                         early_stopping=False, random_state=7)
