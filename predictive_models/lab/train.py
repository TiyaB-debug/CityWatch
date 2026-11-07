"""Compare rolling weekly cyclist-injury hotspot forecasts."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citywatch import (LAT_ORIGIN, LAT_STEP, LON_ORIGIN, LON_STEP, STATIONS,
                       bike_activity, grid)
from lab.models import baselines, extra_trees, gradient_boosting, logistic, poisson, random_forest

WEEKS = pd.date_range("2023-01-02", "2026-10-26", freq="W-MON")
TRAIN_START = pd.Timestamp("2023-07-03")
VALIDATION = pd.Timestamp("2026-04-06")
TEST = pd.Timestamp("2026-07-06")
BUDGETS = (5, 10, 20)
CRASH = ["latitude", "longitude", "injury_4", "injury_13", "injury_52",
         "all_4", "all_13", "nearby_13", "season_sin", "season_cos"]
WEATHER = ["rain", "wet_days", "temp", "archive_rain"]
COMPLAINT = ["requests_4", "requests_13"]
BIKE = ["bike_endpoints", "bike_available"]


def week_of(values):
    return values.dt.normalize() - pd.to_timedelta(values.dt.dayofweek, unit="D")


def nearby(frame):
    source = frame.set_index(["week", "y", "x"]).injury_13
    result = np.zeros(len(frame))
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        index = pd.MultiIndex.from_arrays([frame.week, frame.y + dy, frame.x + dx])
        result += source.reindex(index, fill_value=0).to_numpy()
    return result


def crash_panel(path):
    columns = ["crash_date", "collision_id", "latitude", "longitude", "number_of_cyclist_injured"]
    crashes = pd.read_csv(path, usecols=columns).drop_duplicates("collision_id")
    crashes["week"] = week_of(pd.to_datetime(crashes.crash_date, format="mixed"))
    crashes["injury"] = crashes.number_of_cyclist_injured.gt(0).astype(int)
    crashes = crashes.loc[crashes.week.isin(WEEKS)]
    mapped = grid(crashes, "latitude", "longitude")
    history = mapped.loc[mapped.week.lt(TRAIN_START)]
    established = history.groupby(["y", "x"]).injury.agg(["size", "sum"])
    cells = established.loc[established["size"].ge(3) | established["sum"].gt(0)].reset_index()[["y", "x"]]
    cells["latitude"] = LAT_ORIGIN + (cells.y + .5) * LAT_STEP
    cells["longitude"] = LON_ORIGIN + (cells.x + .5) * LON_STEP
    cells["cell_id"] = cells.y.astype(str) + "-" + cells.x.astype(str)
    counts = mapped.groupby(["y", "x", "week"]).injury.agg(all_crashes="size", injury="sum")
    rows = cells.merge(pd.DataFrame({"week": WEEKS}), how="cross")
    rows = rows.join(counts, on=["y", "x", "week"])
    rows[["injury", "all_crashes"]] = rows[["injury", "all_crashes"]].fillna(0)
    for field, name, windows in (("injury", "injury", (4, 13, 52)),
                                 ("all_crashes", "all", (4, 13))):
        for window in windows:
            rows[f"{name}_{window}"] = rows.groupby("cell_id")[field].transform(
                lambda series: series.shift(2).rolling(window, min_periods=1).sum()
            ).fillna(0)
    rows["nearby_13"] = nearby(rows)
    phase = rows.week.dt.dayofyear * 2 * np.pi / 365.25
    rows["season_sin"], rows["season_cos"] = np.sin(phase), np.cos(phase)
    return rows, crashes.groupby("week").injury.sum(), len(crashes)


def nearest(latitudes, longitudes, stations):
    locations = list(stations.values())
    lat = latitudes.to_numpy()[:, None]
    lon = longitudes.to_numpy()[:, None]
    distances = (lat - np.array(locations)[:, 0]) ** 2 + (.76 * (lon - np.array(locations)[:, 1])) ** 2
    return np.array(list(stations))[distances.argmin(axis=1)]


def add_weather(rows, modern_path, archive_dir):
    stations = pd.read_csv(modern_path, dtype={"STATION": str})
    stations["date"] = pd.to_datetime(stations.DATE)
    stations["week"] = week_of(stations.date)
    stations["temp"] = (stations.TMAX + stations.TMIN) / 2
    stations["wet"] = stations.PRCP.ge(1).where(stations.PRCP.notna())
    weekly = stations.groupby(["week", "STATION"]).agg(
        rain=("PRCP", "mean"), wet_days=("wet", "mean"), temp=("temp", "mean")
    )
    # Use the most recent fully elapsed week of observed weather.
    rows["weather_week"] = rows.week - pd.Timedelta(days=7)
    rows["station"] = nearest(rows.latitude, rows.longitude, STATIONS)
    rows = rows.join(weekly, on=["weather_week", "station"])
    monthly = []
    locations = {}
    for path in sorted(archive_dir.glob("*.csv")):
        data = pd.read_csv(path, usecols=["STATION", "DATE", "LATITUDE", "LONGITUDE",
                                         "PRCP", "PRCP_ATTRIBUTES"])
        station = str(data.STATION.iloc[0])
        locations[station] = (float(data.LATITUDE.iloc[0]), float(data.LONGITUDE.iloc[0]))
        dates = pd.to_datetime(data.DATE)
        quality = data.PRCP_ATTRIBUTES.fillna("").str.split(",").str[1].fillna("").eq("")
        clean = data.loc[dates.lt("2023-01-01") & data.PRCP.ge(0) & quality].copy()
        clean["month"] = dates.dt.month
        climate = (clean.groupby("month").PRCP.mean() / 10).rename("archive_rain").reset_index()
        monthly.append(climate.assign(archive_station=station))
    rows["archive_station"] = nearest(rows.latitude, rows.longitude, locations)
    rows["month"] = rows.week.dt.month
    rows = rows.join(pd.concat(monthly).set_index(["month", "archive_station"]),
                     on=["month", "archive_station"])
    # Early missing lag values occur during warm-up. Later missing values are reported.
    return rows, locations


def add_complaints(rows, path):
    counts = pd.read_csv(path, parse_dates=["week"]).set_index(["y", "x", "week"]).requests
    metadata = json.loads(path.with_suffix(".json").read_text())
    if not counts.index.is_unique or counts.sum() != metadata["requests_in_study_bounds"]:
        raise ValueError("311 aggregation failed reconciliation")
    rows = rows.join(counts, on=["y", "x", "week"])
    rows["requests"] = rows.requests.fillna(0)
    for window in (4, 13):
        rows[f"requests_{window}"] = rows.groupby("cell_id").requests.transform(
            lambda series: series.shift(2).rolling(window, min_periods=1).sum()
        ).fillna(0)
    return rows, metadata["projected_requests"]


def add_bike(rows, path):
    activity = bike_activity(path)
    rows = rows.join(activity, on=["y", "x"])
    rows["bike_available"] = rows.week.ge("2025-09-01").astype(int)
    rows["bike_endpoints"] = rows.bike_endpoints.fillna(0) * rows.bike_available
    return rows, int(activity.sum())


def model_specs():
    features = CRASH + WEATHER + COMPLAINT + BIKE
    specs = {
        "Poisson": (poisson.build, features, True),
        "Logistic": (logistic.build, features, False),
        "Random forest": (random_forest.build, features, False),
        "Extra trees": (extra_trees.build, features, False),
    }
    specs.update({
        name: (gradient_boosting.build, columns, False)
        for name, columns in gradient_boosting.variants(CRASH, WEATHER, COMPLAINT, BIKE).items()
    })
    return specs


def fit(rows, models):
    train = rows.loc[rows.week.between(TRAIN_START, VALIDATION, inclusive="left")]
    evaluated = rows.loc[rows.week.ge(VALIDATION)].copy()
    baselines.add_scores(evaluated)
    for name, (build, columns, count) in models.items():
        model = build()
        print(f"Fitting {name} on {len(train):,} cell-weeks", flush=True)
        median = train[columns].median().fillna(0)
        x = train[columns].fillna(median)
        future = evaluated[columns].fillna(median)
        with threadpool_limits(limits=4):
            if count:
                model.fit(x, train.injury)
                evaluated[name] = model.predict(future)
            else:
                model.fit(x, train.injury.gt(0))
                evaluated[name] = model.predict_proba(future)[:, 1]
    return evaluated, [*baselines.HISTORY_WINDOWS, *models]


def score(rows, models, denominator, frames=False):
    by_week = list(rows.groupby("week", sort=True))
    total = int(denominator.reindex([week for week, _ in by_week], fill_value=0).sum())
    summary, replay = {}, {}
    for model in models:
        captures = {budget: [] for budget in BUDGETS}
        weeks = []
        for week, data in by_week:
            top = data.sort_values([model, "cell_id"], ascending=[False, True]).head(max(BUDGETS))
            actual = int(denominator.get(week, 0))
            for budget in BUDGETS:
                captures[budget].append(int(top.head(budget).injury.sum()))
            if frames:
                fields = ["cell_id", "latitude", "longitude", "injury", "injury_13", "requests_4",
                          "bike_endpoints", "rain", model]
                clean = top[fields].round(6).astype(object).where(pd.notna(top[fields]), None)
                weeks.append({"date": week.strftime("%Y-%m-%d"), "total": actual,
                              "cells": clean.values.tolist()})
        summary[model] = {
            "average_precision": round(float(average_precision_score(rows.injury.gt(0), rows[model])), 6),
            "capture": {budget: {"count": sum(values), "share": sum(values) / total, "weekly": values}
                        for budget, values in captures.items()},
        }
        if frames:
            replay[model] = weeks
    return summary, replay, total


def paired_interval(replay, test, chosen):
    actual = np.array([week["total"] for week in replay[chosen]])
    delta = (np.array(test[chosen]["capture"][10]["weekly"])
             - np.array(test["13-week baseline"]["capture"][10]["weekly"]))
    rng = np.random.default_rng(42)
    # Circular three-week blocks retain short-range dependence between neighboring weeks.
    starts = rng.integers(len(actual), size=(3000, int(np.ceil(len(actual) / 3))))
    draws = ((starts[:, :, None] + np.arange(3)) % len(actual)).reshape(3000, -1)[:, :len(actual)]
    gaps = delta[draws].sum(axis=1) / actual[draws].sum(axis=1)
    return np.quantile(gaps, [.025, .975]).tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crashes", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--complaints", type=Path, required=True)
    parser.add_argument("--bike-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    specs = model_specs()
    parser.add_argument("--model", action="append", choices=specs,
                        help="Run a named model alongside both baselines. Repeat to compare several.")
    args = parser.parse_args()
    selected_specs = {name: spec for name, spec in specs.items()
                      if args.model is None or name in args.model}
    rows, totals, crash_count = crash_panel(args.crashes)
    rows, stations = add_weather(rows, args.weather, args.archive)
    rows, requests = add_complaints(rows, args.complaints)
    rows, endpoints = add_bike(rows, args.bike_zip)
    evaluated, models = fit(rows, selected_specs)
    validation, _, validation_total = score(evaluated.loc[evaluated.week.lt(TEST)], models, totals)
    chosen = max(models, key=lambda model: (validation[model]["capture"][10]["count"],
                                            validation[model]["average_precision"]))
    test_rows = evaluated.loc[evaluated.week.ge(TEST)]
    test, replay, test_total = score(test_rows, models, totals, frames=True)
    result = {
        "selected": chosen,
        "validation_total": validation_total,
        "test_total": test_total,
        "test_candidate_injuries": int(test_rows.injury.sum()),
        "cells": int(rows.cell_id.nunique()),
        "all_crash_records_in_weeks": crash_count,
        "projected_311_requests": requests,
        "august_bike_endpoints": endpoints,
        "archive_stations": list(stations),
        "weather_missing_test_cell_weeks": int(test_rows[WEATHER].isna().any(axis=1).sum()),
        "validation": validation,
        "test": test,
        "paired_10_share_interval": paired_interval(replay, test, chosen),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "backtest.json").write_text(json.dumps(result, indent=2) + "\n")
    template = Path(__file__).with_name("replay.html").read_text()
    payload = json.dumps({"results": result, "replay": replay, "budgets": BUDGETS,
                          "lat_step": LAT_STEP, "lon_step": LON_STEP}, allow_nan=False)
    (args.out / "citywatch_lab.html").write_text(template.replace("/* DATA */ null", payload))
    print(f"Validation selected {chosen}; test: {test[chosen]['capture'][10]['count']}/{test_total}", flush=True)


if __name__ == "__main__":
    main()
