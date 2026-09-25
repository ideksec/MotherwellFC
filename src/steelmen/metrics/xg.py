"""Expected-goals helpers.

xpoints assumes independent Poisson goal counts at the xG rates — a crude
but standard single-match expected-points model.
"""

import math


def _poisson_pmf(rate: float, k: int) -> float:
    return math.exp(-rate) * rate**k / math.factorial(k)


def xpoints(xg_for: float, xg_against: float, *, max_goals: int = 10) -> float:
    """Expected points from team xG for and against."""
    p_for = [_poisson_pmf(max(xg_for, 0.0), k) for k in range(max_goals + 1)]
    p_against = [_poisson_pmf(max(xg_against, 0.0), k) for k in range(max_goals + 1)]
    win = draw = 0.0
    for i, pf in enumerate(p_for):
        for j, pa in enumerate(p_against):
            if i > j:
                win += pf * pa
            elif i == j:
                draw += pf * pa
    return 3 * win + draw


def xg_diff(xg_for: float, xg_against: float) -> float:
    return round(xg_for - xg_against, 2)
