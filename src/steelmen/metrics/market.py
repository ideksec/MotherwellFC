"""Bookmaker odds -> probabilities. Overround is removed proportionally."""


def implied_probabilities(home: float, draw: float, away: float) -> dict:
    """Decimal odds -> fair probabilities (sum to 1). Raises on non-positive odds."""
    if min(home, draw, away) <= 0:
        raise ValueError("Decimal odds must be positive")
    raw = {"home": 1 / home, "draw": 1 / draw, "away": 1 / away}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()} | {"overround": round(total - 1, 4)}


def moneyline_to_decimal(moneyline: float) -> float:
    """American odds -> decimal: -120 -> 1.833, +300 -> 4.0."""
    if moneyline == 0:
        raise ValueError("Moneyline cannot be zero")
    return 1 + (moneyline / 100 if moneyline > 0 else 100 / abs(moneyline))
