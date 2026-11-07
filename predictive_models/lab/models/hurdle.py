"""Separate the chance of any crash from the number of crashes if one occurs."""
from sklearn.base import BaseEstimator, RegressorMixin

from . import logistic, poisson


class HurdleRegressor(RegressorMixin, BaseEstimator):
    def fit(self, x, y):
        positive = y.gt(0)
        self.occurrence_ = logistic.build().fit(x, positive)
        self.excess_ = poisson.build().fit(x.loc[positive], y.loc[positive] - 1)
        return self

    def predict(self, x):
        probability = self.occurrence_.predict_proba(x)[:, 1]
        return probability * (1 + self.excess_.predict(x))


def build():
    return HurdleRegressor()
