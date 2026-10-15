"""Conservative gradient-boosted tree candidate."""
from sklearn.ensemble import HistGradientBoostingClassifier


def make_model():
    # Very small boosting steps reduce overconfident probabilities on noisy monthly labels.
    return HistGradientBoostingClassifier(
        max_iter=30,
        learning_rate=0.01,
        max_leaf_nodes=3,
        min_samples_leaf=100,
        l2_regularization=5.0,
        early_stopping=False,
        random_state=7,
    )
