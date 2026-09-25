"""One figure per match: the event timeline and where it leaves the form line."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from steelmen.metrics.form import through_match  # noqa: E402
from steelmen.viz.palette import (  # noqa: E402
    AMBER,
    CLARET,
    CLARET_SOFT,
    MUTED,
    OPPONENT,
    OPPONENT_SOFT,
    RESULT_COLOURS,
    apply_style,
)

GOAL_KINDS = {"goal", "penalty_goal", "own_goal"}


def _timeline(ax, pack: dict) -> None:
    match = pack["match"]
    opp = match["opponent"]["name"]
    ax.set_xlim(0, 96)
    ax.set_ylim(-1.6, 1.6)
    ax.set_yticks([1, -1])
    ax.set_yticklabels(["Motherwell", opp])
    ax.axhline(0, color=MUTED, linewidth=0.6)
    ax.axvline(45, color=MUTED, linewidth=0.6, linestyle=":")
    ax.set_xticks([0, 15, 30, 45, 60, 75, 90])
    ax.set_xlabel("minute")
    ax.grid(False)
    for event in pack["events"]:
        minute = event.get("minute")
        if minute is None or event.get("team") is None:
            continue
        y = 1 if event["team"] == "motherwell" else -1
        strong = CLARET if y == 1 else OPPONENT
        soft = CLARET_SOFT if y == 1 else OPPONENT_SOFT
        kind = event["kind"]
        if kind in GOAL_KINDS:
            if kind == "own_goal":
                # an own goal is credited to the other side on the scoreboard
                y, strong = -y, (OPPONENT if y == 1 else CLARET)
            ax.scatter([minute], [y], s=140, color=strong, zorder=3, marker="o")
            label = (event.get("player") or "").split(" ")[-1]
            if kind == "penalty_goal":
                label += " (p)"
            if kind == "own_goal":
                label += " (og)"
            ax.annotate(
                label,
                (minute, y),
                textcoords="offset points",
                xytext=(0, 12 if y == 1 else -16),
                ha="center",
                fontsize=8,
                color=strong,
            )
        elif kind in {"yellow_card", "second_yellow"}:
            ax.scatter([minute], [y * 0.55], s=40, color=AMBER, marker="s", zorder=2)
        elif kind == "red_card":
            ax.scatter([minute], [y * 0.55], s=40, color="#B91C1C", marker="s", zorder=2)
        elif kind == "substitution":
            ax.scatter([minute], [y * 0.25], s=18, color=soft, marker="^", zorder=1)
    score = pack["match"]["score"]
    ax.set_title(
        f"Motherwell {score['motherwell']}–{score['opponent']} {opp} · {match['date']} "
        f"· {match['competition']['name']}",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )


def _form_line(ax, pack: dict, matchlog: pd.DataFrame) -> None:
    log = through_match(matchlog, espn_id=pack["match"]["espn_id"])
    log = log.tail(12).reset_index(drop=True)
    x = list(range(len(log)))
    xg_diff = pd.to_numeric(log["motherwell_xg"], errors="coerce") - pd.to_numeric(
        log["opponent_xg"], errors="coerce"
    )
    goal_diff = pd.to_numeric(log["motherwell_goals"], errors="coerce") - pd.to_numeric(
        log["opponent_goals"], errors="coerce"
    )
    colours = [RESULT_COLOURS.get(str(r), MUTED) for r in log["result"]]
    ax.bar(x, goal_diff, color=colours, alpha=0.75, width=0.6, label="goal difference")
    if xg_diff.notna().any():
        ax.plot(x, xg_diff, color=CLARET, marker="o", linewidth=1.5, label="xG difference")
    ax.axhline(0, color=MUTED, linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            f"{'v' if h == 'home' else '@'} {str(o)[:3].upper()}"
            for h, o in zip(log["home_away"], log["opponent"])
        ],
        rotation=45,
        ha="right",
        fontsize=8,
    )
    ax.set_ylabel("per match")
    ax.set_title(
        "Last matches: goal difference (bars) and xG difference (line)", loc="left", fontsize=10
    )
    ax.legend(loc="upper left", fontsize=8)


def match_figure(pack: dict, matchlog: pd.DataFrame, out_path: Path) -> Path:
    apply_style(plt)
    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, figsize=(9, 6.5), gridspec_kw={"height_ratios": [1.0, 1.3]}
    )
    _timeline(ax_top, pack)
    _form_line(ax_bottom, pack, matchlog)
    fig.text(
        0.99,
        0.01,
        "ESPN box score · xG: football-data.co.uk · steelmen",
        ha="right",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
