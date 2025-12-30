"""
G-code analysis utilities.

Reads a G-code file and derives basic statistics such as XY extents,
estimated drawing time, and total travel distances.
"""
import logging
import math
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .config_service import config_service

logger = logging.getLogger(__name__)

_DRAW_CMDS = {"G1", "G01"}
_TRAVEL_CMDS = {"G0", "G00"}


def _extract_float(prefix: str, text: str) -> Optional[float]:
    """Extract a float that immediately follows the given prefix (e.g., X, Y, F)."""
    match = re.search(rf"{prefix}(-?\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _update_bounds(bounds: Optional[Dict[str, float]], x: float, y: float) -> Dict[str, float]:
    """Expand the bounding box to include the provided point."""
    if bounds is None:
        return {"minX": x, "maxX": x, "minY": y, "maxY": y}
    return {
        "minX": min(bounds["minX"], x),
        "maxX": max(bounds["maxX"], x),
        "minY": min(bounds["minY"], y),
        "maxY": max(bounds["maxY"], y),
    }


def analyze_gcode_file(
    file_path: Path,
    draw_feed_mm_per_min: Optional[float] = None,
    travel_feed_mm_per_min: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Analyze a G-code file and return statistics about its motion.

    Args:
        file_path: Path to the G-code file to analyze.
        draw_feed_mm_per_min: Optional override for draw/feed moves (mm/min).
        travel_feed_mm_per_min: Optional override for travel/rapid moves (mm/min).

    Returns:
        Dictionary containing bounds, distances, feed rates, and time estimates.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"G-code file not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError("G-code file is empty")

    # Seed feed rates from the default plotter configuration when available.
    default_plotter = config_service.get_default_plotter()
    default_draw_feed = draw_feed_mm_per_min
    default_travel_feed = travel_feed_mm_per_min

    if default_plotter:
        default_draw_feed = default_draw_feed or (default_plotter.pen_speed * 60.0)
        default_travel_feed = default_travel_feed or (default_plotter.max_speed * 60.0)

    default_draw_feed = default_draw_feed or 1200.0  # reasonable pen speed (~20 mm/s)
    default_travel_feed = default_travel_feed or 6000.0  # faster travel (~100 mm/s)

    current_draw_feed = default_draw_feed
    current_travel_feed = default_travel_feed

    lines_processed = 0
    move_commands = 0
    pen_moves = 0
    travel_moves = 0
    total_distance = 0.0
    pen_distance = 0.0
    travel_distance = 0.0
    estimated_time_seconds = 0.0
    bounds: Optional[Dict[str, float]] = None
    absolute_mode = True
    x = 0.0
    y = 0.0

    min_feed = None
    max_feed = None
    feed_sum = 0.0
    feed_samples = 0

    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            lines_processed += 1
            clean = raw_line.split(";", 1)[0].strip()
            if not clean:
                continue

            if re.search(r"\bG90\b", clean, re.IGNORECASE):
                absolute_mode = True
            elif re.search(r"\bG91\b", clean, re.IGNORECASE):
                absolute_mode = False

            cmd_match = re.search(r"\bG0?0\b|\bG0?1\b", clean, re.IGNORECASE)
            if not cmd_match:
                continue

            cmd = cmd_match.group(0).upper()

            f_value = _extract_float("F", clean)
            if f_value and f_value > 0:
                if cmd in _DRAW_CMDS:
                    current_draw_feed = f_value
                else:
                    current_travel_feed = f_value
                min_feed = f_value if min_feed is None else min(min_feed, f_value)
                max_feed = f_value if max_feed is None else max(max_feed, f_value)
                feed_sum += f_value
                feed_samples += 1

            next_x_val = _extract_float("X", clean)
            next_y_val = _extract_float("Y", clean)

            if absolute_mode:
                next_x = x if next_x_val is None else next_x_val
                next_y = y if next_y_val is None else next_y_val
            else:
                next_x = x + (next_x_val or 0.0)
                next_y = y + (next_y_val or 0.0)

            if math.isclose(next_x, x) and math.isclose(next_y, y):
                continue

            bounds = _update_bounds(bounds, x, y)
            bounds = _update_bounds(bounds, next_x, next_y)

            distance = math.hypot(next_x - x, next_y - y)
            total_distance += distance
            move_commands += 1

            pen_down = cmd in _DRAW_CMDS
            if pen_down:
                pen_moves += 1
                pen_distance += distance
                feed_mm_per_min = current_draw_feed or default_draw_feed
            else:
                travel_moves += 1
                travel_distance += distance
                feed_mm_per_min = current_travel_feed or default_travel_feed

            speed_mm_s = max(feed_mm_per_min / 60.0, 0.001)
            estimated_time_seconds += distance / speed_mm_s

            x, y = next_x, next_y

    width = height = None
    if bounds:
        width = bounds["maxX"] - bounds["minX"]
        height = bounds["maxY"] - bounds["minY"]

    avg_feed = feed_sum / feed_samples if feed_samples else None

    return {
        "lines_processed": lines_processed,
        "move_commands": move_commands,
        "pen_moves": pen_moves,
        "travel_moves": travel_moves,
        "total_distance_mm": round(total_distance, 4),
        "pen_distance_mm": round(pen_distance, 4),
        "travel_distance_mm": round(travel_distance, 4),
        "bounds": bounds,
        "width_mm": round(width, 4) if width is not None else None,
        "height_mm": round(height, 4) if height is not None else None,
        "estimated_time_seconds": round(estimated_time_seconds, 3),
        "estimated_time_minutes": round(estimated_time_seconds / 60.0, 3),
        "average_feedrate_mm_per_min": round(avg_feed, 2) if avg_feed else None,
        "max_feedrate_mm_per_min": round(max_feed, 2) if max_feed else None,
        "min_feedrate_mm_per_min": round(min_feed, 2) if min_feed else None,
        "feedrate_assumptions_mm_per_min": {
            "draw": round(default_draw_feed, 2),
            "travel": round(default_travel_feed, 2),
        },
        "absolute_mode": absolute_mode,
    }



