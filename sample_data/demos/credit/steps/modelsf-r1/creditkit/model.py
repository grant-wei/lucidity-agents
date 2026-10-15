"""The model: a boosted-tree classifier with the sklearn fit/predict_proba interface."""
from sklearn.ensemble import HistGradientBoostingClassifier


def make_model():
    # Shallow, regularized trees capture nonlinear repayment patterns while limiting
    # overfitting; probabilities are optimized directly with dev log loss.
    return HistGradientBoostingClassifier(
        learning_rate=0.06,
        max_iter=250,
        max_leaf_nodes=15,
        min_samples_leaf=40,
        l2_regularization=2.0,
        early_stopping=False,
        random_state=17,
    )
