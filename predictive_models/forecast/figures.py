"""Render individual model figures and the forecast-scenario inspection map."""
import json
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "previous_month_baseline": "Previous-month collision baseline",
    "poisson_no_weather": "Poisson without weather",
    "poisson_weather": "Poisson with weather",
    "boosted_no_weather": "Boosted Poisson without weather",
    "boosted_weather": "Boosted Poisson with weather",
}


def render(output, metrics, future, methods):
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    geometry = json.loads((ROOT / "forecast/inputs/manhattan.geojson").read_text())
    outlines = [polygon[0] for polygon in geometry["coordinates"]]
    cells = future.groupby("cell_id").first()
    totals = future.groupby("cell_id")[methods[1:]].sum()
    totals[methods[0]] = cells[methods[0]]
    holdout = metrics["holdout"]
    for method in methods:
        figure = Figure(figsize=(10, 5.6), facecolor="#f3f7f8")
        FigureCanvasAgg(figure)
        map_ax, chart = figure.subplots(1, 2)
        figure.subplots_adjust(top=.72, bottom=.17, wspace=.32)
        figure.text(.08, .92, LABELS[method], fontsize=20, fontweight="bold", color="#173743")
        figure.text(.08, .85, f"CityWatch Manhattan · {metrics['overlap_start']} to {metrics['overlap_end']} data overlap",
                    fontsize=10, color="#45606b")
        for outline in outlines:
            map_ax.add_patch(Polygon(outline, facecolor="#dce8eb", edgecolor="#9cb3bb", linewidth=.45))
        picks = cells.loc[totals[method].sort_values(ascending=False, kind="stable").head(10).index]
        map_ax.scatter(picks.longitude, picks.latitude, marker="s", s=24, color="#087e84")
        map_ax.set(xlim=(-74.023, -73.90), ylim=(40.695, 40.887), aspect=1/.76)
        map_ax.set_axis_off()
        map_ax.set_title("10 inspection picks · forecast scenario", fontsize=11)
        map_ax.text(.5, -.025, f"{metrics['forecast_start']} to {metrics['forecast_end']}",
                    transform=map_ax.transAxes, ha="center", fontsize=9)
        labels = [row["month"] + ("*" if row["days"] < 28 else "") for row in holdout]
        for budget, color in ((5, "#6c57a5"), (10, "#087e84")):
            share = [100 * row["captured"][method][budget] / max(row["total"], 1) for row in holdout]
            chart.plot(labels, share, marker="o", color=color, label=f"{budget} locations")
        if method != methods[0]:
            baseline = [100 * row["captured"][methods[0]][10] / max(row["total"], 1) for row in holdout]
            chart.plot(labels, baseline, linestyle="--", color="#45606b", label="Baseline · 10")
        chart.set(title="Held-out injury collisions captured", ylabel="Share of reported collisions (%)",
                  xlabel="Prediction month", ylim=(0, None))
        chart.tick_params(axis="x", labelrotation=25, labelsize=8)
        chart.legend(frameon=False, fontsize=8)
        chart.spines[["top", "right"]].set_visible(False)
        figure.text(.08, .035, "* November contains only the overlapping days. Sources: NYC Open Data and NOAA.",
                    fontsize=8, color="#45606b")
        figure.savefig(figures / f"{method}.png", dpi=145)
