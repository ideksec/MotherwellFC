"""Squad usage figure: estimated minutes per player, split starts vs sub minutes."""

from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from steelmen.viz.palette import AMBER, CLARET, MUTED, apply_style


def usage_figure(usage: pd.DataFrame, out_path: Path, *, title: str, max_minutes: int) -> Path:
    apply_style()
    frame = usage.sort_values("minutes_est", ascending=True)
    fig = Figure(figsize=(9, 0.32 * max(len(frame), 6) + 1.2))
    ax = fig.subplots()
    y = range(len(frame))
    ax.barh(y, frame["minutes_est"], color=CLARET, label="estimated minutes")
    ax.scatter(
        frame["goals"] * 0 + max_minutes + 12,
        y,
        s=[max(g, 0) * 40 for g in frame["goals"]],
        color=AMBER,
        label="goals (size)",
        zorder=3,
    )
    ax.set_yticks(list(y))
    ax.set_yticklabels(frame["name"], fontsize=8)
    ax.set_xlim(0, max_minutes + 25)
    ax.axvline(max_minutes, color=MUTED, linewidth=0.6, linestyle=":")
    ax.set_xlabel("estimated minutes (dotted line = every minute available)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    return out_path
