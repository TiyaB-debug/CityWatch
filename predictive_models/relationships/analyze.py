"""Analyze historical relationships across the complete crash and weather overlap."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forecast.run import grid, load, locations

RAIN = ["Dry (<1 mm)", "Light (1–9.9 mm)", "Heavy (≥10 mm)"]
TEMP = ["Below 5 °C", "5–14.9 °C", "15–24.9 °C", "25 °C or above"]
HISTORY = ["0", "1", "2–3", "4 or more"]
BLUE = "#087e84"
INK = "#173743"
MUTED = "#536d76"


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


def spatial_history(mapped, dates):
    cells = locations(mapped)[["y", "x", "first_seen"]]
    counts = mapped.assign(month=mapped.date.dt.to_period("M")).groupby(["month", "y", "x"]).injury.sum()
    frames = []
    for month in dates.to_period("M").unique()[1:]:
        days = int((dates.to_period("M") == month).sum())
        active = cells.loc[cells.first_seen.lt(month.start_time)].copy()
        keys = pd.MultiIndex.from_arrays([np.repeat(month, len(active)), active.y, active.x])
        previous = pd.MultiIndex.from_arrays([np.repeat(month-1, len(active)), active.y, active.x])
        active["prior"] = counts.reindex(previous, fill_value=0).to_numpy()
        active["injuries"] = counts.reindex(keys, fill_value=0).to_numpy()
        active["cell_days"] = days
        frames.append(active)
    sample = pd.concat(frames, ignore_index=True)
    sample["history"] = pd.cut(sample.prior, [-1, 0, 1, 3, np.inf], labels=HISTORY)
    grouped = sample.groupby("history", observed=False).agg(
        injuries=("injuries", "sum"), cell_days=("cell_days", "sum"), cell_months=("injuries", "size"))
    return [{"prior_injuries": label, "injuries": int(row.injuries),
             "cell_days": int(row.cell_days), "cell_months": int(row.cell_months),
             "injuries_per_1000_cell_days": float(1000 * row.injuries / row.cell_days)}
            for label, row in grouped.iterrows()]


def figure(title, subtitle, width=9):
    fig = Figure(figsize=(width, 4.7), facecolor="#f3f7f8")
    FigureCanvasAgg(fig)
    fig.text(.09, .93, title, fontsize=19, fontweight="bold", color=INK)
    fig.text(.09, .862, subtitle, fontsize=9.5, color=MUTED)
    return fig


def polish(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)


def draw_timeline(out, daily):
    monthly = daily.resample("MS").agg(injuries=("injuries", "mean"),
                                       temperature=("temperature_c", "mean"),
                                       rain=("rain_mm", lambda values: 100 * values.ge(1).mean()))
    fig = figure("Cyclist injury collisions over time",
                 "NYC monthly daily averages · Jan 2023–Nov 3, 2026 · November includes three days")
    axes = fig.subplots(3, 1, sharex=True)
    fig.subplots_adjust(top=.77, bottom=.15, left=.13, right=.95, hspace=.35)
    for ax, field, label in zip(axes, ["injuries", "temperature", "rain"],
                                ["Injury collisions/day", "Temperature (°C)", "Wet days (%)"]):
        ax.plot(monthly.index[:-1], monthly[field].iloc[:-1], color=BLUE, linewidth=1.8)
        ax.scatter(monthly.index[-1], monthly[field].iloc[-1], color="#b84719", s=24, zorder=4)
        ax.set_ylabel(label, fontsize=8)
        ax.grid(axis="y", alpha=.22)
        polish(ax)
    axes[-1].set_xlabel("Calendar month")
    fig.text(.13,.045,"Orange marks partial November. Sources: NYC Open Data crash reports and NOAA observations.",
             fontsize=8,color=MUTED)
    fig.savefig(out / "timeline.png", dpi=150)


def draw_weather(out, effects):
    fig = figure("Weather and daily injury collisions",
                 "Adjusted rate ratios · same year, month and weekday · 95% intervals")
    axes = fig.subplots(1, 2)
    fig.subplots_adjust(top=.75, bottom=.19, left=.17, right=.96, wspace=.62)
    for ax, name, title in zip(axes, ("rain", "temp"), ("Rainfall", "Temperature")):
        estimates = effects[name]
        for i, row in enumerate(estimates):
            value = row["adjusted_ratio"]
            interval = row["interval"]
            if interval:
                ax.errorbar(value, i, xerr=[[value-interval[0]], [interval[1]-value]],
                            fmt="o", color=BLUE, capsize=3)
            else:
                ax.scatter(value, i, marker="D", color=MUTED, s=24, zorder=4)
        ax.axvline(1, linestyle="--", color=MUTED, linewidth=.8)
        ax.set_yticks(range(len(estimates)), [row["condition"] for row in estimates])
        ax.invert_yaxis()
        ax.set(title=title, xlabel="Rate ratio relative to reference", xlim=(.54, 1.18))
        polish(ax)
    fig.text(.09,.045,"Diamonds indicate reference groups. Observational associations use NYC crashes and NOAA weather.",
             fontsize=8,color=MUTED)
    fig.savefig(out / "weather_relationships.png", dpi=150)


def draw_history(out, history):
    fig = figure("Do recent hotspots stay hotspots?",
                 "Next-month reported cyclist injury collisions by prior-month crash count")
    ax = fig.subplots()
    fig.subplots_adjust(top=.77, bottom=.22, left=.14, right=.95)
    labels = [row["prior_injuries"] for row in history]
    values = [row["injuries_per_1000_cell_days"] for row in history]
    bars = ax.bar(labels, values, color=BLUE, width=.55)
    ax.bar_label(bars, labels=[f"{value:.1f}" for value in values], padding=4)
    ax.set(xlabel="Reported cyclist injury collisions in previous month (count)",
           ylabel="Next-month collisions per 1,000 cell-days", ylim=(0, max(values)*1.16))
    polish(ax)
    fig.text(.14,.05,"Feb 2023–Nov 3, 2026 · candidate cells known at month start · NYC Open Data crash reports",
             fontsize=8,color=MUTED)
    fig.savefig(out / "crash_history_relationship.png", dpi=150)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crashes", type=Path, required=True)
    parser.add_argument("--weather-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    crashes, weather, dates = load(args.crashes, args.weather_dir)
    daily = daily_history(crashes, weather, dates)
    effects = adjusted_weather(daily)
    history = spatial_history(grid(crashes, "latitude", "longitude"), dates)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {"start": str(dates[0].date()), "end": str(dates[-1].date()),
               "days": len(dates), "injury_collisions": int(daily.injuries.sum()),
               "weather": effects, "prior_crash_history": history}
    (args.out / "relationships.json").write_text(json.dumps(summary, indent=2) + "\n")
    draw_timeline(args.out, daily)
    draw_weather(args.out, effects)
    draw_history(args.out, history)


if __name__ == "__main__":
    main()
