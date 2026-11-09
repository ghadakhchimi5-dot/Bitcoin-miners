"""Shared plotting style so every figure in the report looks the same."""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from .config import path

# Fixed categorical order (validated CVD-safe for adjacent series); colour follows the entity.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def set_style() -> None:
    """Thin lines, recessive grid and axes, one sans typeface."""
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": AXIS, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "lines.linewidth": 1.4, "legend.frameon": False,
    })


def label_line_ends(ax, series: dict, colors: dict) -> None:
    """Direct labels at the right end of each line (identity never relies on colour alone)."""
    ends = {n: s.dropna() for n, s in series.items()}
    ends = {n: (s.index[-1], s.iloc[-1]) for n, s in ends.items()}
    for n, (x, y) in ends.items():
        ax.plot(x, y, "o", ms=3, color=colors[n])
    # Push labels apart vertically (in axes fraction) so close series never print on top of each other.
    fig_to_ax = ax.transAxes.inverted()
    pos = sorted((fig_to_ax.transform(ax.transData.transform((mdates.date2num(x), float(y))))[1], n)
                 for n, (x, y) in ends.items())
    min_gap, placed = 0.05, []
    for y, n in pos:
        placed.append([max(y, placed[-1][0] + min_gap) if placed else y, n])
    for (ya, n) in placed:
        x, y = ends[n]
        ax.annotate(f"{n} {y:,.0f}", xy=(x, y), xycoords="data", xytext=(1.01, ya),
                    textcoords=("axes fraction"), va="center", fontsize=8, color=INK2,
                    annotation_clip=False)


def save(fig, name: str) -> str:
    """Save under figures/ with the project's naming convention."""
    f = path("figures") / f"{name}.png"
    fig.savefig(f)
    return str(f.relative_to(path("figures").parent))
