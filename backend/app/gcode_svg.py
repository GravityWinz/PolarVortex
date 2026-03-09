"""Convert G-code into SVG previews. Adapted from Scrible."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Dict, List, Tuple


Point = Tuple[float, float]
_WORD_RE = re.compile(r"([A-Za-z])\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")


@dataclass
class _Move:
    kind: str  # "draw" or "travel"
    points: List[Point]


def _strip_comment(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _parse_words(line: str) -> Dict[str, float]:
    words: Dict[str, float] = {}
    for letter, number in _WORD_RE.findall(line):
        words[letter.upper()] = float(number)
    return words


def _format_num(value: float) -> str:
    return f"{value:.3f}"


def _arc_polyline(
    start: Point,
    end: Point,
    center: Point,
    cw: bool,
) -> List[Point]:
    sx, sy = start
    ex, ey = end
    cx, cy = center
    r_start = math.hypot(sx - cx, sy - cy)
    r_end = math.hypot(ex - cx, ey - cy)
    radius = max(1e-9, 0.5 * (r_start + r_end))
    start_ang = math.atan2(sy - cy, sx - cx)
    end_ang = math.atan2(ey - cy, ex - cx)

    if cw:
        while end_ang >= start_ang:
            end_ang -= 2.0 * math.pi
        sweep = start_ang - end_ang
        direction = -1.0
    else:
        while end_ang <= start_ang:
            end_ang += 2.0 * math.pi
        sweep = end_ang - start_ang
        direction = 1.0

    if sweep < 1e-6:
        return [start, end]

    # Approximate every 5 degrees max for visibly smooth arcs.
    steps = max(8, min(720, int(math.ceil(sweep / (math.pi / 36.0)))))
    pts: List[Point] = []
    for i in range(steps + 1):
        t = i / float(steps)
        ang = start_ang + direction * sweep * t
        pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    pts[-1] = end
    return pts


def _parse_moves(gcode_text: str) -> List[_Move]:
    x = 0.0
    y = 0.0
    absolute_mode = True
    pen_is_down = False
    pen_up_servo: float | None = None
    pen_down_servo: float | None = None
    moves: List[_Move] = []

    for raw_line in gcode_text.splitlines():
        line = _strip_comment(raw_line)
        if not line:
            continue
        words = _parse_words(line)
        if "G" in words:
            gnum = int(round(words["G"]))
            cmd = f"G{gnum}"
        elif "M" in words:
            mnum = int(round(words["M"]))
            cmd = f"M{mnum}"
        else:
            continue

        if cmd == "G90":
            absolute_mode = True
            continue
        if cmd == "G91":
            absolute_mode = False
            continue

        if cmd == "M280" and "S" in words:
            servo = words["S"]
            if pen_up_servo is None:
                pen_up_servo = servo
                pen_is_down = False
                continue
            if pen_down_servo is None and not math.isclose(servo, pen_up_servo):
                pen_down_servo = servo
                pen_is_down = True
                continue
            if pen_down_servo is not None and math.isclose(servo, pen_down_servo):
                pen_is_down = True
                continue
            if pen_up_servo is not None and math.isclose(servo, pen_up_servo):
                pen_is_down = False
                continue

        if cmd not in {"G0", "G1", "G2", "G3"}:
            continue

        prev = (x, y)
        if absolute_mode:
            nx = words.get("X", x)
            ny = words.get("Y", y)
        else:
            nx = x + words.get("X", 0.0)
            ny = y + words.get("Y", 0.0)
        nxt = (nx, ny)

        if cmd in {"G0", "G1"}:
            if not (math.isclose(prev[0], nxt[0]) and math.isclose(prev[1], nxt[1])):
                kind = "travel" if (cmd == "G0" or not pen_is_down) else "draw"
                moves.append(_Move(kind=kind, points=[prev, nxt]))
            x, y = nx, ny
            continue

        # G2/G3 arcs with I/J center offsets from start point.
        if "I" not in words or "J" not in words:
            if not (math.isclose(prev[0], nxt[0]) and math.isclose(prev[1], nxt[1])):
                kind = "draw" if pen_is_down else "travel"
                moves.append(_Move(kind=kind, points=[prev, nxt]))
            x, y = nx, ny
            continue

        center = (prev[0] + words["I"], prev[1] + words["J"])
        arc_pts = _arc_polyline(prev, nxt, center, cw=(cmd == "G2"))
        kind = "draw" if pen_is_down else "travel"
        moves.append(_Move(kind=kind, points=arc_pts))
        x, y = nx, ny

    return moves


def _to_svg_path(
    points: List[Point],
    *,
    min_x: float,
    min_y: float,
    margin: float,
) -> str:
    if not points:
        return ""
    x0 = points[0][0] - min_x + margin
    y0 = (-points[0][1]) - min_y + margin
    out = [f"M {_format_num(x0)} {_format_num(y0)}"]
    for x, y in points[1:]:
        sx = x - min_x + margin
        sy = (-y) - min_y + margin
        out.append(f"L {_format_num(sx)} {_format_num(sy)}")
    return " ".join(out)


def gcode_to_svg_string(
    gcode_text: str,
    *,
    draw_stroke_width_mm: float = 0.35,
) -> str:
    """Convert G-code text into an SVG preview string."""
    moves = _parse_moves(gcode_text)

    all_points: List[Point] = []
    for move in moves:
        if len(move.points) < 2:
            continue
        all_points.extend(move.points)

    if not all_points:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<rect x="0" y="0" width="10" height="10" fill="white"/>'
            "</svg>\n"
        )

    xs = [p[0] for p in all_points]
    ys_svg = [-p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys_svg), max(ys_svg)
    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)
    margin = max(width, height) * 0.02
    vb_w = width + 2.0 * margin
    vb_h = height + 2.0 * margin
    draw_paths: List[str] = []
    travel_paths: List[str] = []
    for move in moves:
        path_d = _to_svg_path(
            move.points,
            min_x=min_x,
            min_y=min_y,
            margin=margin,
        )
        if not path_d:
            continue
        if move.kind == "draw":
            draw_paths.append(path_d)
        else:
            travel_paths.append(path_d)

    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{_format_num(vb_w)}mm" height="{_format_num(vb_h)}mm" '
            f'viewBox="0 0 {_format_num(vb_w)} {_format_num(vb_h)}" '
            f'preserveAspectRatio="xMidYMid meet">'
        ),
        '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
    ]
    if travel_paths:
        lines.append('<g fill="none" stroke="#dddddd" stroke-width="0.20">')
        for d in travel_paths:
            lines.append(f'<path d="{d}"/>')
        lines.append("</g>")
    if draw_paths:
        draw_width = max(0.01, float(draw_stroke_width_mm))
        lines.append(
            f'<g fill="none" stroke="#111111" stroke-width="{_format_num(draw_width)}">'
        )
        for d in draw_paths:
            lines.append(f'<path d="{d}"/>')
        lines.append("</g>")
    lines.append("</svg>")
    lines.append("")
    return "\n".join(lines)
