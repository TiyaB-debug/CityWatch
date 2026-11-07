"""Backtest daily crash-count forecasts and score future weather scenarios."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import STATIONS, load_overlap, locations, manhattan_crashes
from models.inspection import specifications
from forecast.figures import render

VALIDATION = pd.Timestamp("2026-01-01")
HOLDOUT = pd.Timestamp("2026-07-01")
BASELINE = "previous_month_baseline"
METHODS = [BASELINE, *specifications()]
BUDGETS = (5, 10)


def snapshot(cells, monthly, origin):
    known = cells.loc[cells.first_seen.lt(origin)].copy()
    previous = origin - pd.offsets.MonthBegin()
    recent = origin - pd.offsets.MonthBegin(3)
    history = monthly.loc[monthly.month.lt(origin)]
    for frame, field, name in (
        (history.loc[history.month.eq(previous)], "injury", "prior_injuries"),
        (history.loc[history.month.eq(previous)], "crashes", "prior_crashes"),
        (history.loc[history.month.ge(recent)], "injury", "recent_injuries"),
        (history, "injury", "history_injuries"),
    ):
        values = frame.groupby(["y", "x"])[field].sum().rename(name)
        known = known.join(values, on=["y", "x"])
        known[name] = known[name].fillna(0)
    return known


def panel(known, weather):
    dates = pd.DataFrame({"date": sorted(weather.date.unique())})
    rows = dates.merge(known.drop(columns="first_seen"), how="cross")
    rows = rows.join(weather.set_index(["date", "station"]), on=["date", "station"], validate="many_to_one")
    if not np.isfinite(rows[["rain_mm", "temperature_c"]]).all().all():
        raise ValueError("Missing or invalid weather for candidate days")
    phase = rows.date.dt.dayofyear * 2 * np.pi / 365.25
    rows["weekend"] = rows.date.dt.dayofweek.ge(5)
    rows["season_sin"], rows["season_cos"] = np.sin(phase), np.cos(phase)
    rows["wet"] = rows.rain_mm.ge(1)
    return rows


def fit_predict(train, target):
    target[BASELINE] = target.prior_injuries
    for name, (columns, model) in specifications().items():
        print(f"Fitting {name} on {len(train):,} cell-days", flush=True)
        x = train[columns].to_numpy(dtype=np.float32)
        future = target[columns].to_numpy(dtype=np.float32)
        with threadpool_limits(limits=4):
            model.fit(x, train.injury)
            target[name] = model.predict(future)


def evaluate(scored, mapped, crashes):
    results = []
    for month, rows in scored.groupby(scored.date.dt.to_period("M"), sort=True):
        start, end = rows.date.min(), rows.date.max()
        observed = mapped.loc[mapped.date.between(start, end)].groupby("cell_id").injury.sum()
        total = int(crashes.loc[crashes.date.between(start, end), "injury"].sum())
        totals = rows.groupby("cell_id")[METHODS[1:]].sum()
        totals[BASELINE] = rows.groupby("cell_id")[BASELINE].first()
        captured = {}
        for model in METHODS:
            ranks = totals[model].sort_values(ascending=False, kind="stable")
            captured[model] = {budget: int(observed.reindex(ranks.head(budget).index, fill_value=0).sum())
                               for budget in BUDGETS}
        results.append({"month": str(month), "days": rows.date.nunique(), "total": total, "captured": captured})
    return results


def scenario_weather(args, weather, cutoff):
    if args.forecast:
        scenario = pd.read_csv(args.forecast, parse_dates=["date"], dtype={"station": str})
        label = "User-supplied forecast"
    else:
        scenario = weather.loc[weather.date.gt(cutoff - pd.Timedelta(days=7))].copy()
        scenario["date"] += args.scenario_start - scenario.date.min()
        label = "Simulated weather from the final seven observed days"
    scenario = scenario[["date", "station", "rain_mm", "temperature_c"]]
    if (scenario.empty or scenario.date.min() <= cutoff
        or scenario.date.dt.to_period("M").nunique() != 1
        or scenario.duplicated(["date", "station"]).any()
        or not scenario.groupby("date").station.apply(lambda x: set(x) == set(STATIONS)).all()
        or not np.isfinite(scenario[["rain_mm", "temperature_c"]]).all().all()
        or scenario.rain_mm.lt(0).any()):
        raise ValueError("Forecast needs future dates in one month and valid weather for all three stations each day")
    return scenario, label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crashes", type=Path, required=True)
    parser.add_argument("--weather-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    forecast = parser.add_mutually_exclusive_group(required=True)
    forecast.add_argument("--forecast", type=Path, help="CSV with date, station, rain_mm, temperature_c")
    forecast.add_argument("--scenario-start", type=pd.Timestamp, help="First day for a seven-day weather simulation")
    args = parser.parse_args()
    crashes, weather, dates = load_overlap(args.crashes, args.weather_dir)
    crashes, mapped = manhattan_crashes(crashes)
    mapped["cell_id"] = mapped.y.astype(str) + "-" + mapped.x.astype(str)
    mapped["month"] = mapped.date.dt.to_period("M").dt.to_timestamp()
    cells = locations(mapped)
    monthly = mapped.groupby(["month", "y", "x"]).injury.agg(injury="sum", crashes="size").reset_index()
    daily = mapped.groupby(["date", "y", "x"]).injury.sum()
    panels = []
    for month, conditions in weather.groupby(weather.date.dt.to_period("M")):
        known = snapshot(cells, monthly, month.start_time)
        if not known.empty:
            panels.append(panel(known, conditions))
    historical = pd.concat(panels, ignore_index=True)
    del panels
    historical = historical.join(daily, on=["date", "y", "x"])
    historical["injury"] = historical.injury.fillna(0).astype("int8")
    fit_data = historical.loc[historical.date.lt(VALIDATION)]
    scored = historical.loc[historical.date.ge(VALIDATION)].copy()
    fit_predict(fit_data, scored)
    del fit_data
    months = evaluate(scored, mapped, crashes)
    del scored
    validation = [row for row in months if row["month"] < str(HOLDOUT.to_period("M"))]
    test = [row for row in months if row["month"] >= str(HOLDOUT.to_period("M"))]
    selected = max(METHODS[1:], key=lambda model: sum(row["captured"][model][10] for row in validation))
    scenario, label = scenario_weather(args, weather, dates[-1])
    # Later scenarios may extend beyond the snapshot. Freeze crash features
    # at the latest issue date supported by a complete prior calendar month.
    cutoff_month = dates[-1].to_period("M")
    last_issue = cutoff_month.start_time
    if dates[-1].day == dates[-1].days_in_month:
        last_issue = (cutoff_month + 1).start_time
    origin = min(scenario.date.min().to_period("M").start_time, last_issue)
    future = panel(snapshot(cells, monthly, origin), scenario)
    fit_predict(historical, future)
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = {"scope": "Manhattan borough", "overlap_start": str(dates[0].date()), "overlap_end": str(dates[-1].date()),
               "backtest_training_start": str(historical.date.min().date()),
               "backtest_training_end": str((VALIDATION - pd.Timedelta(days=1)).date()),
               "forecast_training_end": str(dates[-1].date()),
               "selected_on_validation": selected, "validation": validation, "holdout": test,
               "forecast_start": str(scenario.date.min().date()), "forecast_end": str(scenario.date.max().date()),
               "forecast_weather": label, "overlapping_crash_records": len(crashes)}
    (args.out / "backtest.json").write_text(json.dumps(metrics, indent=2) + "\n")
    scenario.to_csv(args.out / "forecast_weather.csv", index=False, date_format="%Y-%m-%d")
    future[["cell_id", "latitude", "longitude", "date", "rain_mm", "temperature_c", *METHODS]].to_csv(
        args.out / "daily_forecasts.csv", index=False, float_format="%.9g", date_format="%Y-%m-%d")
    render(args.out, metrics, future, METHODS)


if __name__ == "__main__":
    main()
