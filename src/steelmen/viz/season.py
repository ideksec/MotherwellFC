"""Season form chart for the site: cumulative points vs cumulative xPts (league)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from steelmen.metrics.xg import xpoints  # noqa: E402
from steelmen.viz.palette import AMBER, CLARET, MUTED, RESULT_COLOURS, apply_style  # noqa: E402


def form_figure(matchlog: pd.DataFrame, out_path: Path, *, competition: str = "sco.1") -> Path:
    apply_style(plt)
    log = matchlog[matchlog["competition_code"] == competition].copy()
    log = log.sort_values(["kickoff_utc", "espn_id"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 4.5))
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
            xpts = [
                xpoints(f, a) if pd.notna(f) and pd.notna(a) else None
                for f, a in zip(xg_for, xg_against)
            ]
            cumulative, total = [], 0.0
            for value in xpts:
                total += value or 0.0
                cumulative.append(total)
            ax.plot(x, cumulative, color=AMBER, linewidth=2, linestyle="--", label="xPts")
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
    plt.close(fig)
    return out_path
