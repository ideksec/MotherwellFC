"""Figures. All renderers use the Agg backend and the claret/amber palette."""

from steelmen.viz.match import match_figure
from steelmen.viz.season import form_figure
from steelmen.viz.usage import usage_figure

__all__ = ["form_figure", "match_figure", "usage_figure"]
