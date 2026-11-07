"""Estimate collision probability with randomized tree splits."""
from sklearn.ensemble import ExtraTreesClassifier


def build():
    return ExtraTreesClassifier(
        n_estimators=55, max_depth=15, min_samples_leaf=35, n_jobs=4, random_state=42,
    )
