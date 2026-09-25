"""Season form chart for the site: cumulative points vs cumulative xPts (league)."""

import math
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from steelmen.metrics.xg import xpoints
from steelmen.viz.palette import AMBER, CLARET, MUTED, RESULT_COLOURS, apply_style


def form_figure(matchlog: pd.DataFrame, out_path: Path, *, competition: str = "sco.1") -> Path:
    """Cumulative points vs cumulative xPts. The xPts line stops at the first
    match without xG rather than pretending missing xG is zero."""
    apply_style()
    log = matchlog[matchlog["competition_code"] == competition].copy()
    log = log.sort_values(["kickoff_utc", "espn_id"]).reset_index(drop=True)
    fig = Figure(figsize=(9, 4.5))
    ax = fig.subplots()
    if log.empty:
        ax.text(0.5, 0.5, "No league matches yet", ha="center", va="center", color=MUTED)
        ax.set_axis_off()
    else:
        points = pd.to_numeric(log["points"], errors="coerce").fillna(0).cumsum()
        x = list(range(1, len(log) + 1))
        ax.step(x, points, where="mid", color=CLARET, linewidth=2, label="points")
        xg_for = pd.to_numeric(log["motherwell_xg"], errors="coerce")
        xg_against = pd.to_numeric(log["opponent_xg"], errors="coerce")
        if xg_for.notna().any():
            cumulative, total, stopped = [], 0.0, False
            for f, a in zip(xg_for, xg_against):
                if stopped or pd.isna(f) or pd.isna(a):
                    stopped = True
                    cumulative.append(math.nan)
                    continue
                total += xpoints(float(f), float(a))
                cumulative.append(total)
            ax.plot(x, cumulative, color=AMBER, linewidth=2, linestyle="--", label="xPts")
            if stopped:
                ax.text(
                    0.99,
                    0.02,
                    "xPts line stops where xG is not yet published",
                    transform=ax.transAxes,
                    ha="right",
                    fontsize=8,
                    color=MUTED,
                )
        for xi, result in zip(x, log["result"]):
            colour = RESULT_COLOURS.get(str(result), MUTED)
            ax.scatter([xi], [points.iloc[xi - 1]], color=colour, s=30, zorder=3)
        ax.set_xlabel("league match")
        ax.set_ylabel("cumulative")
        ax.set_xticks(x)
        ax.set_title("Premiership points vs expected points (xPts)", loc="left", fontweight="bold")
        ax.legend(loc="upper left")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    return out_path
