"""Daily count estimators for the overlapping-date forecast."""
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CRASH = ["latitude", "longitude", "prior_injuries", "prior_crashes",
         "recent_injuries", "history_injuries", "weekend", "season_sin", "season_cos"]
WEATHER = ["rain_mm", "temperature_c", "wet"]


def boosted():
    return HistGradientBoostingRegressor(loss="poisson", max_iter=55, max_leaf_nodes=20,
                                         min_samples_leaf=200, l2_regularization=1, random_state=42)


def specifications():
    return {
        "poisson_no_weather": (CRASH, make_pipeline(StandardScaler(), PoissonRegressor(alpha=.003))),
        "poisson_weather": (CRASH + WEATHER,
                            make_pipeline(StandardScaler(), PoissonRegressor(alpha=.003))),
        "boosted_no_weather": (CRASH, boosted()),
        "boosted_weather": (CRASH + WEATHER, boosted()),
    }
