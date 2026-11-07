"""CityWatch daily weather associations."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

RAIN = ["Dry (<1 mm)", "Light (1–9.9 mm)", "Heavy (≥10 mm)"]
TEMP = ["Below 5 °C", "5–14.9 °C", "15–24.9 °C", "25 °C or above"]

def daily_history(crashes, weather, dates):
    daily = pd.DataFrame(index=dates)
    daily["injuries"] = crashes.groupby("date").injury.sum().reindex(dates, fill_value=0)
    daily = daily.join(weather.groupby("date")[["rain_mm", "temperature_c"]].mean())
    daily["rain"] = pd.cut(daily.rain_mm, [-np.inf, 1, 10, np.inf], labels=RAIN, right=False)
    daily["temp"] = pd.cut(daily.temperature_c, [-np.inf, 5, 15, 25, np.inf], labels=TEMP, right=False)
    daily["year"], daily["month"], daily["weekday"] = daily.index.year, daily.index.month, daily.index.dayofweek
    return daily


def adjusted_weather(daily):
    formula = ("injuries ~ C(rain, Treatment(reference=0)) + C(temp, Treatment(reference=2)) "
               "+ C(year) + C(month) + C(weekday)")
    fit = smf.glm(formula, data=daily, family=sm.families.Poisson()).fit(
        cov_type="HAC", cov_kwds={"maxlags": 7}
    )
    intervals = fit.conf_int()
    results = {}
    for name, labels, reference in (("rain", RAIN, 0), ("temp", TEMP, 2)):
        terms = iter([term for term in fit.params.index if term.startswith(f"C({name},")])
        counts = daily.groupby(name, observed=False).injuries.agg(["size", "mean"])
        estimates = []
        for index, label in enumerate(labels):
            term = None if index == reference else next(terms)
            ratio = 1.0 if term is None else float(np.exp(fit.params[term]))
            bounds = None if term is None else np.exp(intervals.loc[term]).tolist()
            estimates.append({"condition": label, "days": int(counts.loc[label, "size"]),
                              "raw_daily_mean": float(counts.loc[label, "mean"]),
                              "adjusted_ratio": ratio, "interval": bounds})
        results[name] = estimates
    return results
