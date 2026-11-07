"""Estimate the chance of at least one injury collision with logistic regression."""
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def build():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=350))
