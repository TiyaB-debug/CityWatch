"""Draw separate September shortlist and capture figures."""
import json
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

OUTLINES = Path(__file__).with_name("inputs") / "nyc_borough_outlines.json"
TEAL = "#087e84"
ORANGE = "#b84719"
MUTED = "#45606b"
INK = "#173743"
PAPER = "#f3f7f8"


def write_figures(directory, cells, rankings, observed, metrics, methods):
    directory.mkdir(parents=True, exist_ok=True)
    outlines = json.loads(OUTLINES.read_text())
    locations = cells.set_index("cell_id")
    baseline = set(rankings["baseline"])
    for model, label in methods.items():
        figure = Figure(figsize=(11, 6), facecolor=PAPER)
        FigureCanvasAgg(figure)
        map_ax, chart = figure.subplots(1, 2, gridspec_kw={"width_ratios": [1.1, 1]})
        figure.subplots_adjust(left=.07, right=.96, top=.76, bottom=.19, wspace=.3)
        figure.text(.07, .94, "CITYWATCH  /  AUGUST TRAINING · SEPTEMBER HOLDOUT", color=TEAL,
                    fontsize=10, fontweight="bold")
        figure.text(.07, .864, label, color=INK, fontsize=23, fontweight="bold")
        for outline in outlines:
            map_ax.add_patch(Polygon(outline, closed=True, facecolor="#dce8eb",
                                    edgecolor="#9cb3bb", linewidth=.45))
        chosen = set(rankings[model])
        for cell in sorted(chosen | baseline):
            point = locations.loc[cell]
            color = TEAL if cell in chosen - baseline else ORANGE if cell in baseline - chosen else MUTED
            hit = observed.get(cell, 0) > 0
            map_ax.scatter(point.longitude, point.latitude, s=28, marker="s", edgecolor=color,
                           facecolor=color if hit else "none", linewidth=1.15, zorder=3)
        map_ax.set(xlim=(-74.27, -73.68), ylim=(40.48, 40.93), aspect=1/.76)
        map_ax.set_axis_off()
        map_ax.set_title(f"Top 10 inspection cells · {len(chosen - baseline)} swaps",
                         loc="left", fontsize=11, color=INK)
        map_ax.legend(handles=[
            Line2D([], [], marker="s", linestyle="", color=TEAL, label="Added by method"),
            Line2D([], [], marker="s", linestyle="", color=ORANGE, label="August baseline only"),
            Line2D([], [], marker="s", linestyle="", color=MUTED, label="Picked by both"),
        ], loc="upper center", bbox_to_anchor=(.5, -.025), frameon=False, fontsize=8, ncols=3)

        counts = metrics["monthly_top_k"]
        total = metrics["september_reported_injury_collisions"]
        for index, budget in enumerate((5, 10)):
            baseline_share = 100 * counts["baseline"][budget]["share"]
            share = 100 * counts[model][budget]["share"]
            chart.barh(index+.16, baseline_share, height=.27, color=MUTED, label="August baseline" if not index else None)
            chart.barh(index-.16, share, height=.27, color=TEAL, label=label if not index else None)
            for value, position, key in ((baseline_share, index+.16, "baseline"), (share, index-.16, model)):
                chart.text(value+.016, position, f"{counts[key][budget]['captured']}/{total}",
                           va="center", fontsize=9, color=INK)
        maximum = max(100 * result[budget]["share"] for result in counts.values() for budget in (5,10))
        chart.set(xlim=(0, maximum * 1.36), xlabel="Share of September injury collisions (%)")
        chart.set_yticks([0, 1], ["5 locations", "10 locations"])
        chart.set_title("September collisions captured", loc="left", fontsize=11, color=INK)
        chart.spines[["top", "right"]].set_visible(False)
        chart.legend(loc="upper center", bbox_to_anchor=(.5, -.23), frameon=False, fontsize=8, ncols=2)
        figure.text(.07, .045, "Filled squares mark cells with a reported September injury collision. "
                    "Sources: NYC Open Data crashes and borough boundaries, NOAA daily summaries.",
                    color=MUTED, fontsize=8)
        figure.savefig(directory / f"{model}.png", dpi=150)
