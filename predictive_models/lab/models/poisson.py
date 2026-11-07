"""Predict the number of cyclist injury collisions per cell-week."""
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def build():
    return make_pipeline(StandardScaler(), PoissonRegressor(alpha=.04))
