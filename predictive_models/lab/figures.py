"""Render a standalone hotspot and holdout figure for each ranking method."""
import json
import re
from datetime import date
from itertools import accumulate
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from lab.features import LAT_STEP, LON_STEP

INK = "#173743"
MUTED = "#45606b"
TEAL = "#087e84"
ORANGE = "#b84719"
PAPER = "#f3f7f8"
OUTLINES = Path(__file__).with_name("inputs") / "nyc_borough_outlines.json"


def draw_maps(figure, grid, frames, outlines):
    for column, index in enumerate((0, len(frames) // 2, len(frames) - 1)):
        frame = frames[index]
        ax = figure.add_subplot(grid[0, column], facecolor=PAPER)
        for outline in outlines:
            ax.add_patch(Polygon(outline, closed=True, facecolor="#dce8eb",
                                 edgecolor="#9cb3bb", linewidth=.45))
        picks = frame["cells"][:10]
        for lat, lon, injuries in picks:
            bounds = [[lon-LON_STEP/2, lat-LAT_STEP/2], [lon+LON_STEP/2, lat-LAT_STEP/2],
                      [lon+LON_STEP/2, lat+LAT_STEP/2], [lon-LON_STEP/2, lat+LAT_STEP/2]]
            ax.add_patch(Polygon(bounds, closed=True, facecolor=ORANGE if injuries else "none",
                                 edgecolor=ORANGE if injuries else TEAL, linewidth=1.35, zorder=3))
        ax.set(xlim=(-74.27, -73.68), ylim=(40.48, 40.93), aspect=1/.76)
        ax.set_axis_off()
        week = date.fromisoformat(frame["date"])
        captured = int(sum(cell[2] for cell in picks))
        ax.set_title(f"Week of {week:%b %d}  ·  {captured} captured",
                     color=INK, fontsize=11, loc="left", pad=7)


def draw_capture(ax, frames, metrics, baseline):
    weeks = [date.fromisoformat(frame["date"]) for frame in frames]
    for budget, color in ((5, "#6c57a5"), (10, TEAL), (20, "#1c4d83")):
        weekly = metrics["capture"][budget]["weekly"]
        ax.plot(weeks, list(accumulate(weekly)), color=color, linewidth=2,
                label=f"{budget} cells per week")
    if metrics is not baseline:
        ax.plot(weeks, list(accumulate(baseline["capture"][10]["weekly"])), color=MUTED,
                linestyle="--", linewidth=1.5, label="52-week baseline · 10 cells")
    ax.set_title("Cumulative injury collisions captured", loc="left", color=INK,
                 fontsize=12, fontweight="bold")
    ax.set(xlabel="Holdout week starting (2026)", ylabel="Collisions captured (count)", ylim=(0, None))
    ticks = weeks[::4]
    ax.set_xticks(ticks, [week.strftime("%b %d") for week in ticks])
    ax.grid(axis="y", color="#d9e4e7")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.legend(loc="upper left", frameon=False, fontsize=9, ncols=2)


def write_figures(directory, result, frames_by_model):
    directory.mkdir(parents=True, exist_ok=True)
    outlines = json.loads(OUTLINES.read_text())
    baseline = result["test"]["52-week baseline"]
    for model, frames in frames_by_model.items():
        metrics = result["test"][model]
        figure = Figure(figsize=(11, 8), facecolor=PAPER)
        FigureCanvasAgg(figure)
        grid = figure.add_gridspec(2, 3, height_ratios=(1, 1.05), hspace=.47,
                                  left=.09, right=.96, top=.79, bottom=.12)
        figure.text(.09, .947, "CITYWATCH  /  WEEKLY INSPECTION BACKTEST", color=TEAL,
                    fontsize=10, fontweight="bold")
        figure.text(.09, .894, model, color=INK, fontsize=25, fontweight="bold")
        captured = metrics["capture"][10]["count"]
        figure.text(.09, .851, f"{captured} of {result['test_total']:,} reported injury collisions captured"
                    "  ·  10 inspections per week  ·  Jul 6–Nov 1, 2026", color=MUTED, fontsize=11)
        draw_maps(figure, grid, frames, outlines)
        figure.legend(handles=[
            Line2D([], [], marker="s", linestyle="", markerfacecolor="none",
                   markeredgecolor=TEAL, label="Recommended cell"),
            Line2D([], [], marker="s", linestyle="", color=ORANGE,
                   label="Recommended cell with an observed injury collision"),
        ], loc="upper left", bbox_to_anchor=(.083, .50), ncols=2, frameon=False, fontsize=9)
        draw_capture(figure.add_subplot(grid[1, :], facecolor=PAPER), frames, metrics, baseline)
        figure.text(.09, .039, "Source: CityWatch holdout · NYC Open Data crashes. "
                    "Borough outlines: NYC Department of City Planning.", color=MUTED, fontsize=8)
        filename = re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_") + ".png"
        figure.savefig(directory / filename, dpi=150)
