"""Estimate collision probability with a bootstrap ensemble of decision trees."""
from sklearn.ensemble import RandomForestClassifier


def build():
    return RandomForestClassifier(
        n_estimators=55, max_depth=13, min_samples_leaf=35,
        max_samples=.45, n_jobs=4, random_state=42,
    )
