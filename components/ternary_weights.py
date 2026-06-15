"""ternary_weights.py — Streamlit custom component for interactive MMR weight selection.

Renders an SVG ternary triangle in an iframe. The user clicks or drags a
marker to pick three weights (w_prob, w_div, w_ad) that sum to exactly 1.0,
each snapped to a 0.05 grid (i.e. integer multiples of 1/20).

Communication protocol
  Python → JS:  w_prob, w_div, w_ad (floats) + locked_c (bool)
  JS → Python:  { i, j, k }  integers with i + j + k == 20
"""

from __future__ import annotations

import os
import pathlib
import streamlit.components.v1 as components

_FRONTEND_DIR = str(pathlib.Path(__file__).parent / "ternary_weights_html")

# Streamlit serves the files in _FRONTEND_DIR as static assets for the iframe.
_component_fn = components.declare_component(
    "ternary_weights",
    path=_FRONTEND_DIR,
)


def ternary_weights(
    w_prob: float = 0.50,
    w_div: float = 0.25,
    w_ad: float = 0.25,
    locked_c: bool = False,
    key: str | None = None,
) -> tuple[float, float, float]:
    """Interactive ternary weight selector.

    Renders a triangle with axes Activity (w_prob), Diversity (w_div), and
    AD score (w_ad). The user clicks anywhere inside the triangle to teleport
    the marker to the nearest grid point, or drags the marker while snapping
    live. Python session state is updated only on mouseup / touchend — exactly
    one Streamlit rerun per user interaction.

    Args:
        w_prob:   Current activity weight (shown as initial marker position).
        w_div:    Current diversity weight.
        w_ad:     Current AD-score weight.
        locked_c: When True, the AD axis is locked to 0 (no training set).
                  The marker is constrained to the Activity-Diversity edge.
        key:      Streamlit widget key for identity across reruns.

    Returns:
        (w_prob, w_div, w_ad) reflecting the latest user interaction.
        Each value is a multiple of 0.05 and the three values sum to 1.0
        (within floating-point precision).  If no interaction has occurred yet,
        the input values are returned unchanged.
    """
    result = _component_fn(
        w_prob=float(w_prob),
        w_div=float(w_div),
        w_ad=float(w_ad),
        locked_c=bool(locked_c),
        key=key,
        default=None,
    )

    if result is None:
        # Component has not fired yet (first render before any interaction).
        return float(w_prob), float(w_div), float(w_ad)

    i = max(0, min(20, int(result["i"])))
    j = max(0, min(20, int(result["j"])))
    k = max(0, min(20, int(result["k"])))

    if i + j + k != 20:
        # Should never happen — JS guarantees i+j+k=20, but guard anyway.
        return float(w_prob), float(w_div), float(w_ad)

    return i / 20.0, j / 20.0, k / 20.0
