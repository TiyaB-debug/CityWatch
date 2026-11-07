"""Fit the August 2025 CityWatch pilot and score the September holdout."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.features import LAT_ORIGIN, LAT_STEP, LON_ORIGIN, LON_STEP, STATIONS, grid
from lab.figures import write_figures
from lab.models import baselines, poisson, weather_rates

AUGUST = pd.date_range("2025-08-01", "2025-08-31")
SEPTEMBER = pd.date_range("2025-09-01", "2025-09-30")
METHODS = {
    baselines.NAME: "August collision baseline",
    "no_weather": "Poisson without weather",
    "with_weather": "Poisson with weather",
    "weather_rates": "Wet/dry collision rates",
}
BUDGETS = (5, 10)
SCORES = [key for key in METHODS if key != baselines.NAME]


def load_crashes(path):
    columns = ["crash_date", "collision_id", "latitude", "longitude", "number_of_cyclist_injured"]
    crashes = pd.read_csv(path, usecols=columns).drop_duplicates("collision_id")
    crashes["date"] = pd.to_datetime(crashes.crash_date, format="mixed").dt.normalize()
    crashes["injuries"] = crashes.number_of_cyclist_injured.gt(0).astype(int)
    return crashes.loc[crashes.date.isin(AUGUST.union(SEPTEMBER))]


def load_weather(path):
    daily = pd.read_csv(path, dtype={"STATION": str})
    daily["date"] = pd.to_datetime(daily.DATE)
    daily["temperature_c"] = (daily.TMAX + daily.TMIN) / 2
    daily = daily.rename(columns={"STATION": "station", "PRCP": "rain_mm"})
    return daily.set_index(["date", "station"])[["rain_mm", "temperature_c"]]


def candidates(august):
    cells = august.groupby(["y", "x"]).injuries.agg(august_collisions="sum", august_all_crashes="size").reset_index()
    cells["august_other_crashes"] = cells.august_all_crashes - cells.august_collisions
    cells["cell_id"] = cells.y.astype(str) + "-" + cells.x.astype(str)
    cells["latitude"] = LAT_ORIGIN + (cells.y + .5) * LAT_STEP
    cells["longitude"] = LON_ORIGIN + (cells.x + .5) * LON_STEP
    cells["station"] = [
        min(STATIONS, key=lambda name: (lat - STATIONS[name][0]) ** 2
            + (.76 * (lon - STATIONS[name][1])) ** 2)
        for lat, lon in zip(cells.latitude, cells.longitude)
    ]
    return cells


def panel(cells, dates, weather):
    rows = pd.DataFrame({"date": dates}).merge(cells, how="cross")
    rows = rows.join(weather, on=["date", "station"], validate="many_to_one")
    values = rows[["rain_mm", "temperature_c"]]
    if not np.isfinite(values.to_numpy()).all() or values.rain_mm.lt(0).any():
        raise ValueError("Expected valid weather observations for every candidate day")
    return rows


def evaluate(test, cells, observed, denominator):
    totals = test.groupby("cell_id")[SCORES].sum().reindex(cells.cell_id)
    totals[baselines.NAME] = cells.set_index("cell_id")[baselines.COLUMN]
    rankings = {}
    metrics = {}
    for method in METHODS:
        ranked = totals[method].sort_values(ascending=False, kind="stable")
        rankings[method] = ranked.head(max(BUDGETS)).index.tolist()
        metrics[method] = {}
        for budget in BUDGETS:
            captured = int(observed.reindex(rankings[method][:budget], fill_value=0).sum())
            metrics[method][budget] = {"captured": captured, "share": captured / denominator}
    return rankings, metrics


def write_map(output, test, cells, september, metrics):
    payload = {
        "cells": cells.to_dict(orient="records"),
        "dates": {day.strftime("%Y-%m-%d"): rows[["rain_mm", "temperature_c", *SCORES]].values.tolist()
                  for day, rows in test.groupby("date", sort=True)},
        "observed": [[row.date.strftime("%Y-%m-%d"), row.latitude, row.longitude]
                     for row in september.itertuples(index=False)],
        "results": metrics,
        "lat_step": LAT_STEP,
        "lon_step": LON_STEP,
    }
    template = Path(__file__).with_name("map.html").read_text()
    (output / "citywatch_map.html").write_text(
        template.replace("/* CITYWATCH_DATA */ null", json.dumps(payload, allow_nan=False))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crashes", type=Path, required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    crashes = load_crashes(args.crashes)
    mapped = grid(crashes, "latitude", "longitude")
    august = mapped.loc[mapped.date.isin(AUGUST)]
    september = mapped.loc[mapped.date.isin(SEPTEMBER) & mapped.injuries.gt(0)].copy()
    denominator = int(crashes.loc[crashes.date.isin(SEPTEMBER), "injuries"].sum())
    if not august.injuries.any() or not denominator:
        raise ValueError("Expected reported cyclist injury collisions in both months")
    cells = candidates(august)
    weather = load_weather(args.weather)
    train = panel(cells, AUGUST, weather)
    train = train.join(august.groupby(["date", "y", "x"]).injuries.sum(), on=["date", "y", "x"])
    train["injuries"] = train.injuries.fillna(0)
    test = panel(cells, SEPTEMBER, weather)
    with threadpool_limits(limits=4):
        test["no_weather"] = poisson.predict(train, test, False)
        test["with_weather"] = poisson.predict(train, test, True)
    test["weather_rates"] = weather_rates.predict(train, test)
    september["cell_id"] = september.y.astype(str) + "-" + september.x.astype(str)
    observed = september.groupby("cell_id").size()
    rankings, capture = evaluate(test, cells, observed, denominator)
    metrics = {"august_mapped_injury_collisions": int(august.injuries.sum()),
               "september_reported_injury_collisions": denominator,
               "september_mapped_injury_collisions": len(september),
               "candidate_cells": len(cells), "monthly_top_k": capture}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "backtest.json").write_text(json.dumps(metrics, indent=2) + "\n")
    test[["cell_id", "latitude", "longitude", "date", "with_weather"]].to_csv(
        args.out / "daily_with_weather_sep_2025.csv", index=False, float_format="%.10g"
    )
    write_map(args.out, test, cells, september, metrics)
    write_figures(args.out / "figures", cells, rankings, observed, metrics, METHODS)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
