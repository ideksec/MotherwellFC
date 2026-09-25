"""Claret and amber, plus neutrals that read on light and dark backgrounds."""

CLARET = "#7A1E2C"
AMBER = "#F5B41E"
CLARET_SOFT = "#B8606C"
AMBER_SOFT = "#F8D27A"
OPPONENT = "#6B7280"
OPPONENT_SOFT = "#B0B5BD"
INK = "#1C1A17"
MUTED = "#6B655C"
GRID = "#E2DED7"
PAPER = "#FBFAF8"

RESULT_COLOURS = {"W": "#1C6B3F", "D": AMBER, "L": CLARET}


def apply_style(target=None) -> None:
    """Set the lab's matplotlib style. Accepts pyplot for backwards compatibility;
    by default it updates matplotlib.rcParams without importing pyplot, so
    importing steelmen.viz never changes a notebook's backend."""
    import matplotlib

    params = target.rcParams if target is not None else matplotlib.rcParams
    params.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "font.size": 10,
            "font.family": "sans-serif",
            "legend.frameon": False,
        }
    )
