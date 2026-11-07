"""Fit CityWatch on August 2025 and replay September inspection decisions."""
import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import PoissonRegressor

AUGUST = pd.date_range("2025-08-01", "2025-08-31")
SEPTEMBER = pd.date_range("2025-09-01", "2025-09-30")
LAT_ORIGIN, LON_ORIGIN = 40.48, -74.27
LAT_STEP, LON_STEP = 0.0045, 0.0059
STATIONS = {
    "USW00094728": (40.779, -73.969),
    "USW00014732": (40.779, -73.880),
    "USW00094789": (40.639, -73.762),
}


def grid(frame, latitude, longitude):
    lat = pd.to_numeric(frame[latitude], errors="coerce")
    lon = pd.to_numeric(frame[longitude], errors="coerce")
    valid = lat.between(40.48, 40.93) & lon.between(-74.27, -73.68)
    result = frame.loc[valid].copy()
    result["y"] = ((lat[valid] - LAT_ORIGIN) / LAT_STEP).astype(int)
    result["x"] = ((lon[valid] - LON_ORIGIN) / LON_STEP).astype(int)
    return result


def read_crashes(path):
    frame = pd.read_csv(path, low_memory=False)
    frame.columns = frame.columns.str.strip().str.lower().str.replace(" ", "_")
    frame["date"] = pd.to_datetime(frame.crash_date, format="mixed").dt.normalize()
    return frame.loc[
        frame.date.isin(AUGUST.union(SEPTEMBER)) & frame.number_of_cyclist_injured.gt(0)
    ].drop_duplicates("collision_id")


def bike_activity(path):
    totals = []
    columns = ["started_at", "ended_at", "start_lat", "start_lng", "end_lat", "end_lng"]
    with zipfile.ZipFile(path) as archive:
        files = [name for name in archive.namelist()
                 if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")]
        if not files:
            raise ValueError("Citi Bike archive contains no CSV files")
        for name in files:
            with archive.open(name) as source:
                for chunk in pd.read_csv(source, usecols=columns, chunksize=200_000):
                    for endpoint, timestamp in [("start", "started_at"), ("end", "ended_at")]:
                        dates = chunk[timestamp].str[:10]
                        subset = chunk.loc[dates.between("2025-08-01", "2025-08-31")]
                        points = grid(subset, endpoint + "_lat", endpoint + "_lng")
                        totals.append(points.groupby(["y", "x"]).size())
    return pd.concat(totals).groupby(level=["y", "x"]).sum().rename("bike_endpoints")


def read_weather(path):
    weather = pd.read_csv(path, dtype={"STATION": str})
    weather["date"] = pd.to_datetime(weather.DATE)
    weather = weather.loc[weather.STATION.isin(STATIONS)].copy()
    weather["temperature_c"] = (weather.TMAX + weather.TMIN) / 2
    weather = weather.rename(columns={"PRCP": "rain_mm", "STATION": "station"})
    weather = weather.set_index(["date", "station"])
    values = weather[["rain_mm", "temperature_c"]]
    if values.empty or not values.index.is_unique or values.isna().any().any():
        raise ValueError("Weather needs unique, complete station-day measurements")
    if not np.isfinite(values.to_numpy()).all() or values.rain_mm.lt(0).any():
        raise ValueError("Weather contains invalid measurements")
    return values


def location_features(august, bikes, stations):
    counts = august.groupby(["y", "x"]).size().rename("august_collisions")
    cells = pd.concat([counts, bikes], axis=1).fillna(0).astype(int).reset_index()
    cells = cells.sort_values(["y", "x"]).reset_index(drop=True)
    cells["cell_id"] = cells.y.astype(str) + "-" + cells.x.astype(str)
    cells["latitude"] = LAT_ORIGIN + (cells.y + 0.5) * LAT_STEP
    cells["longitude"] = LON_ORIGIN + (cells.x + 0.5) * LON_STEP
    cells["station"] = [
        min(stations, key=lambda station: (lat - STATIONS[station][0]) ** 2
            + (0.76 * (lon - STATIONS[station][1])) ** 2)
        for lat, lon in zip(cells.latitude, cells.longitude)
    ]
    return cells


def panel(cells, dates, weather):
    rows = pd.DataFrame({"date": dates}).merge(cells, how="cross")
    rows = rows.join(weather, on=["date", "station"])
    if rows[["rain_mm", "temperature_c"]].isna().any().any():
        raise ValueError("Weather is missing a required date for a selected station")
    return rows


def features(rows, use_weather):
    for cell, station, endpoints, date, rain, temp in zip(
        rows.cell_id, rows.station, rows.bike_endpoints, rows.date,
        rows.rain_mm, rows.temperature_c,
    ):
        activity = np.log1p(endpoints) / 10
        result = {"cell=" + cell: 10.0, "station=" + station: 1.0,
                  "activity": activity, "weekend": float(date.dayofweek >= 5)}
        if use_weather:
            wet = float(rain >= 1)
            temperature = (temp - 20) / 10
            result.update(wet=wet, temperature=temperature,
                          rain_intensity=np.log1p(rain) / 3,
                          wet_activity=wet * activity,
                          temperature_activity=temperature * activity)
            result["wet_station=" + station] = wet
        yield result


def fit_predict(train, test, use_weather):
    vectorizer = DictVectorizer()
    matrix = vectorizer.fit_transform(features(train, use_weather))
    model = PoissonRegressor(alpha=0.001, max_iter=1000, tol=1e-7)
    model.fit(matrix, train.collisions)
    return model.predict(vectorizer.transform(features(test, use_weather)))


def evaluate(test, september, denominator):
    observed = september.groupby(["y", "x"]).size()
    totals = test.groupby(["y", "x"])[["no_weather", "with_weather"]].sum()
    totals["baseline"] = test.groupby(["y", "x"]).august_collisions.first()
    results = {}
    for model in ["baseline", "no_weather", "with_weather"]:
        ranked = totals[model].sort_values(ascending=False, kind="stable")
        results[model] = {}
        for budget in (5, 10):
            captured = int(observed.reindex(ranked.head(budget).index, fill_value=0).sum())
            results[model][budget] = {
                "captured": captured, "share": round(captured / denominator, 6)
            }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crashes", required=True, type=Path)
    parser.add_argument("--weather", required=True, type=Path)
    parser.add_argument("--bike-zip", required=True, type=Path)
    parser.add_argument("--out", default=Path("output"), type=Path)
    args = parser.parse_args()

    crashes = read_crashes(args.crashes)
    mapped = grid(crashes, "latitude", "longitude")
    august = mapped.loc[mapped.date.isin(AUGUST)]
    september = mapped.loc[mapped.date.isin(SEPTEMBER)]
    denominator = int(crashes.date.isin(SEPTEMBER).sum())
    if august.empty or not denominator:
        raise ValueError("Both August and September crash records are required")
    weather = read_weather(args.weather)
    cells = location_features(august, bike_activity(args.bike_zip),
                              sorted(set(weather.index.get_level_values("station"))))
    train = panel(cells, AUGUST, weather)
    test = panel(cells, SEPTEMBER, weather)
    # August outcomes enter only as training labels and as the count baseline.
    train = train.join(august.groupby(["date", "y", "x"]).size().rename("collisions"),
                       on=["date", "y", "x"])
    train["collisions"] = train.collisions.fillna(0)
    test["no_weather"] = fit_predict(train, test, False)
    test["with_weather"] = fit_predict(train, test, True)

    results = {
        "august_mapped_injury_collisions": len(august),
        "september_reported_injury_collisions": denominator,
        "september_mapped_injury_collisions": len(september),
        "candidate_cells": len(cells),
        "monthly_top_k": evaluate(test, september, denominator),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n")
    test.to_csv(args.out / "daily_scores.csv", index=False, float_format="%.8f")
    write_map(args.out, test, cells, results)
    print(json.dumps(results, indent=2))


def write_map(output, test, cells, results):
    """Bundle the replay data into an HTML file that can be opened directly."""
    template = Path(__file__).with_name("map.html").read_text()
    columns = ["rain_mm", "temperature_c", "no_weather", "with_weather"]
    payload = {
        "cells": cells.to_dict(orient="records"),
        "dates": {
            date.strftime("%Y-%m-%d"): rows[columns].round(8).values.tolist()
            for date, rows in test.groupby("date", sort=True)
        },
        "results": results,
        "lat_step": LAT_STEP,
        "lon_step": LON_STEP,
    }
    (output / "citywatch_map.html").write_text(
        template.replace("/* CITYWATCH_DATA */ null", json.dumps(payload, allow_nan=False))
    )


if __name__ == "__main__":
    main()
