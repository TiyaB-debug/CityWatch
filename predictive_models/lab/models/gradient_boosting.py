"""Gradient boosting and its controlled feature-removal comparisons."""
from sklearn.ensemble import HistGradientBoostingClassifier


def build():
    return HistGradientBoostingClassifier(
        max_iter=95, max_leaf_nodes=15, min_samples_leaf=70,
        l2_regularization=1, early_stopping=False, random_state=42,
    )


def variants(crash, weather, complaints, bike):
    return {
        "Gradient boost": crash + weather + complaints + bike,
        "Boost without weather": crash + complaints + bike,
        "Boost without 311": crash + weather + bike,
        "Boost without Citi Bike": crash + weather + complaints,
        "Boost crash history only": crash,
    }
