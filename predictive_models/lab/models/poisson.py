"""Matched daily Poisson models with and without weather features."""
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import PoissonRegressor


def features(rows, use_weather):
    for row in rows.itertuples(index=False):
        values = {"cell=" + row.cell_id: 10.0, "station=" + row.station: 1.0,
                  "august_other_crashes": np.log1p(row.august_other_crashes),
                  "weekend": float(row.date.dayofweek >= 5)}
        if use_weather:
            wet = float(row.rain_mm >= 1)
            values.update(wet=wet, rain=np.log1p(row.rain_mm),
                          temperature=(row.temperature_c - 20) / 10)
            values["wet_station=" + row.station] = wet
        yield values


def predict(train, target, use_weather):
    vectorizer = DictVectorizer()
    matrix = vectorizer.fit_transform(features(train, use_weather))
    model = PoissonRegressor(alpha=.001, max_iter=1000, tol=1e-7)
    model.fit(matrix, train.injuries)
    return model.predict(vectorizer.transform(features(target, use_weather)))
