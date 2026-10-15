"""Random-forest probability model."""
from sklearn.ensemble import RandomForestClassifier


def make_model():
    # Unweighted trees preserve the low base rate; shallow, leaf-regularized trees
    # avoid spuriously confident probabilities on the short historical sample.
    return RandomForestClassifier(
        n_estimators=800,
        max_features=0.8,
        min_samples_leaf=5,
        max_depth=4,
        class_weight=None,
        random_state=17,
        n_jobs=-1,
    )
