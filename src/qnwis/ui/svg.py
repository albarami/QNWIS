"""
SVG chart renderers for QNWIS UI components.

Provides minimal, dependency-free SVG generators for bar and line charts.
All outputs are deterministic and use no external libraries.
"""

from __future__ import annotations

from typing import Any


def _esc(text: str) -> str:
    """
    Escape XML special characters for safe inclusion in SVG.

    Args:
        text: Raw text to escape

    Returns:
        Escaped text safe for SVG content
    """
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _empty_svg(title: str, width: int, height: int, message: str) -> str:
    """
    Render a simple placeholder SVG when no data is available.
    """
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="{_esc(title)}">',
            f"<title>{_esc(title)}</title>",
            '<rect width="100%" height="100%" fill="white"/>',
            f'<text x="{width/2:.1f}" y="{height/2:.1f}" text-anchor="middle" font-size="12" fill="#666">{_esc(message)}</text>',
            "</svg>",
        ]
    )


def bar_chart_svg(
    title: str,
    categories: list[str],
    values: list[float],
    width: int = 720,
    height: int = 360,
) -> str:
    """
    Return a minimal SVG bar chart as a string. No external libs.

    Args:
        title: Chart title displayed at top
        categories: List of category labels for x-axis
        values: List of numeric values (aligned with categories)
        width: SVG width in pixels (default 720)
        height: SVG height in pixels (default 360)

    Returns:
        SVG markup as string

    Example:
        >>> svg = bar_chart_svg("Test", ["A", "B"], [10.0, 20.0])
        >>> "rect" in svg and "svg" in svg
        True
    """
    pad, bar_gap = 40, 8
    if not values:
        return _empty_svg(title, width, height, "No data available")
    n = max(1, len(values))
    max_v = max(values) if values else 0.0
    bar_w = (width - 2 * pad - (n - 1) * bar_gap) / n
    bars: list[str] = []
    for i, v in enumerate(values):
        x = pad + i * (bar_w + bar_gap)
        h = 0 if max_v <= 0 else (height - 2 * pad) * (float(v) / float(max_v))
        y = height - pad - h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#4e79a7"/>'
        )
        # category labels
        cat_label = categories[i] if i < len(categories) else f"#{i+1}"
        cat = _esc(str(cat_label))
        bars.append(
            f'<text x="{x + bar_w/2:.1f}" y="{height - pad/2:.1f}" font-size="10" text-anchor="middle">{cat}</text>'
        )
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="{_esc(title)}">',
        f"<title>{_esc(title)}</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="20" text-anchor="middle" font-size="14">{_esc(title)}</text>',
        *bars,
        "</svg>",
    ]
    return "\n".join(svg_lines)


def line_chart_svg(
    title: str,
    points: list[dict[str, Any]],
    width: int = 720,
    height: int = 360,
) -> str:
    """
    Return a minimal SVG line chart for points=[{x:int, y:float}].

    Args:
        title: Chart title displayed at top
        points: List of data points, each with "x" and "y" keys
        width: SVG width in pixels (default 720)
        height: SVG height in pixels (default 360)

    Returns:
        SVG markup as string

    Example:
        >>> svg = line_chart_svg("Test", [{"x": 1, "y": 2.0}, {"x": 2, "y": 3.0}])
        >>> "path" in svg and "svg" in svg
        True
    """
    pad = 40
    if not points:
        return _empty_svg(title, width, height, "No data available")
    filtered = [p for p in points if p.get("y") is not None]
    if not filtered:
        return _empty_svg(title, width, height, "No data available")
    xs = [p["x"] for p in filtered if p.get("y") is not None]
    ys = [p["y"] for p in filtered if p.get("y") is not None]
    if not xs or not ys:
        return _empty_svg(title, width, height, "No data available")
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(1, max_x - min_x)
    span_y = max(1e-9, max_y - min_y)
    path_commands: list[str] = []
    for p in sorted(filtered, key=lambda q: q["x"]):
        sx = pad + (float(p["x"]) - min_x) / span_x * (width - 2 * pad)
        sy = height - pad - (float(p["y"]) - min_y) / span_y * (height - 2 * pad)
        cmd = "M" if not path_commands else "L"
        path_commands.append(f"{cmd}{sx:.1f},{sy:.1f}")
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="{_esc(title)}">',
        f"<title>{_esc(title)}</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<path d="{" ".join(path_commands)}" fill="none" stroke="#e15759" stroke-width="2"/>',
        "</svg>",
    ]
    return "\n".join(svg_lines)
