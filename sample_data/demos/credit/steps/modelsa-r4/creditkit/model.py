"""Scaled k-nearest-neighbors credit-risk model."""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer


def make_model():
    # Repayment-status history is ordinal and stable; avoid unrelated dollar
    # magnitude features when comparing customers in the neighborhood.
    columns = [*range(1, 7), 31, 32]
    scale = ColumnTransformer([("history", StandardScaler(), columns)], remainder="drop")
    return make_pipeline(scale, KNeighborsClassifier(n_neighbors=400, weights="uniform", n_jobs=-1))
