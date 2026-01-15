import asyncio
import json
import logging
import re
import shlex
import time
import textwrap
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple

logger = logging.getLogger(__name__)
# Write debug logs inside the repo so paths work in containers and on host
# Persist vpype debug logs inside container storage
LOG_PATH = Path("/app/local_storage/log/vpype.log")
# Store vpype config in persistent local storage so it survives rebuilds
DEFAULT_VPYPE_CONFIG = Path("/app/local_storage/config/vpype.toml")
DEFAULT_GWRITE_PROFILE = "polarvortex"
APP_VERSION = "1.0.0"
def _get_default_gcode_settings():
    try:
        from .config_service import config_service

        plotter = config_service.get_default_plotter()
        if plotter and getattr(plotter, "gcode_sequences", None):
            return plotter.gcode_sequences
    except Exception:
        logger.warning("Falling back to hardcoded vpype defaults", exc_info=True)

    class _Fallback:
        pen_up_command = "M280 P0 S110"
        pen_down_command = "M280 P0 S130"
        on_connect = ["G90", "G21", "M280 P0 S110"]

    return _Fallback()


def _get_stroke_value(elem) -> str:
    """Return the stroke color for an SVG element, falling back to style attr."""
    stroke = elem.get("stroke")
    if stroke:
        return stroke
    style = elem.get("style", "")
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key.strip() == "stroke":
            return value.strip()
    return "none"


# Color name mapping for common hex values
_COLOR_NAME_MAP: Dict[str, str] = {
    "#000000": "Black",
    "#FFFFFF": "White",
    "#FF0000": "Red",
    "#00FF00": "Green",
    "#0000FF": "Blue",
    "#FFFF00": "Yellow",
    "#FF00FF": "Magenta",
    "#00FFFF": "Cyan",
    "#800000": "Maroon",
    "#008000": "Green",
    "#000080": "Navy",
    "#808000": "Olive",
    "#800080": "Purple",
    "#008080": "Teal",
    "#C0C0C0": "Silver",
    "#808080": "Gray",
    "#FFA500": "Orange",
    "#A52A2A": "Brown",
    "#FFC0CB": "Pink",
    "#FFD700": "Gold",
    "#4B0082": "Indigo",
    "#FF1493": "Deep Pink",
    "#00CED1": "Dark Turquoise",
    "#32CD32": "Lime Green",
    "#FF4500": "Orange Red",
    "#8B0000": "Dark Red",
    "#006400": "Dark Green",
    "#00008B": "Dark Blue",
}


def _normalize_color_value(color: str) -> str:
    """
    Normalize various color formats to hex format.
    
    Handles:
    - Hex colors: #FF0000, #F00
    - rgb()/rgba() functions: rgb(255, 0, 0)
    - Named colors: red, blue, etc.
    
    Returns normalized hex format (e.g., "#FF0000") or original if parsing fails.
    """
    if not color or color.lower() == "none":
        return "none"
    
    color = color.strip()
    
    # Already hex format
    if color.startswith("#"):
        # Expand short hex (#F00 -> #FF0000)
        if len(color) == 4:
            return f"#{color[1]}{color[1]}{color[2]}{color[2]}{color[3]}{color[3]}".upper()
        return color.upper()
    
    # rgb() or rgba() format
    rgb_match = re.match(r"rgba?\(([^)]+)\)", color, re.IGNORECASE)
    if rgb_match:
        values = [v.strip() for v in rgb_match.group(1).split(",")]
        try:
            r = int(float(values[0]))
            g = int(float(values[1]))
            b = int(float(values[2]))
            return f"#{r:02X}{g:02X}{b:02X}"
        except (ValueError, IndexError):
            pass
    
    # Named colors (basic set)
    named_colors = {
        "black": "#000000",
        "white": "#FFFFFF",
        "red": "#FF0000",
        "green": "#00FF00",
        "blue": "#0000FF",
        "yellow": "#FFFF00",
        "magenta": "#FF00FF",
        "cyan": "#00FFFF",
        "orange": "#FFA500",
        "purple": "#800080",
        "pink": "#FFC0CB",
        "brown": "#A52A2A",
        "gray": "#808080",
        "grey": "#808080",
    }
    normalized = color.lower().strip()
    if normalized in named_colors:
        return named_colors[normalized]
    
    # Return original if we can't parse it
    return color


def _generate_color_descriptor(stroke_value: str) -> str:
    """
    Generate a color descriptor string in format: "#FF0000 (Red)" or "#FF0000".
    
    Args:
        stroke_value: Raw stroke color value from SVG
        
    Returns:
        Formatted color descriptor string
    """
    if not stroke_value or stroke_value.lower() == "none":
        return "none"
    
    normalized = _normalize_color_value(stroke_value)
    
    # If normalization failed, return original
    if normalized == stroke_value and not normalized.startswith("#"):
        return stroke_value
    
    # Look up color name
    color_name = _COLOR_NAME_MAP.get(normalized)
    
    if color_name:
        return f"{normalized} ({color_name})"
    else:
        return normalized


def sort_svg_by_stroke(
    svg_path: Path,
    tmp_dir: Path = Path("/app/local_storage/tmp"),
    generation_tag: Optional[str] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Reorder drawable SVG elements so they are grouped by stroke color.

    This ensures plotting is done one color at a time before switching pens.
    
    Returns:
        Tuple of (sorted_svg_path, color_metadata)
        color_metadata contains:
        - color_order: List of stroke values in order they appear
        - color_count: Number of unique colors
        - color_descriptors: Dict mapping stroke value to descriptor string
    """
    color_metadata = {
        "color_order": [],
        "color_count": 0,
        "color_descriptors": {},
    }
    
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(svg_path)
        root = tree.getroot()

        drawable_tags = {
            "path",
            "line",
            "polyline",
            "polygon",
            "rect",
            "circle",
            "ellipse",
        }

        def collect_drawable_elements(elem, drawable_list: list):
            """Recursively collect all drawable elements from element tree."""
            tag = elem.tag.rsplit("}", 1)[-1] if "}" in elem.tag else elem.tag
            if tag in drawable_tags:
                drawable_list.append(elem)
            else:
                # Recursively process children (for groups, etc.)
                for child in elem:
                    collect_drawable_elements(child, drawable_list)
        
        # Collect all drawable elements recursively
        all_drawables = []
        for child in root:
            collect_drawable_elements(child, all_drawables)
        
        # Separate preserved elements (non-drawable top-level elements)
        preserved = []
        for child in root:
            tag = child.tag.rsplit("}", 1)[-1] if "}" in child.tag else child.tag
            if tag not in drawable_tags:
                preserved.append(child)
        
        color_order = []
        color_groups: Dict[str, list] = {}

        for elem in all_drawables:
            stroke = _get_stroke_value(elem)
            if stroke not in color_order:
                color_order.append(stroke)
                # Generate descriptor for this color
                color_metadata["color_descriptors"][stroke] = _generate_color_descriptor(stroke)
            color_groups.setdefault(stroke, []).append(elem)

        # If nothing to sort, return original with empty metadata
        if not color_order:
            return svg_path, color_metadata

        # Update metadata
        color_metadata["color_order"] = color_order
        color_metadata["color_count"] = len(color_order)

        # Rebuild child list: keep preserved elements, then grouped drawables by stroke order
        # When we add elements to root, ElementTree automatically removes them from their old parent
        # So we need to clear groups first to avoid issues, or we can just rebuild the tree
        new_children = []
        
        # Add preserved non-drawable elements (defs, namedview, etc.)
        for elem in preserved:
            tag = elem.tag.rsplit("}", 1)[-1] if "}" in elem.tag else elem.tag
            if tag == "g":  # For groups, keep the group but clear its children
                # Create a new group with same attributes but no children
                import xml.etree.ElementTree as ET
                new_g = ET.Element(elem.tag, elem.attrib)
                new_children.append(new_g)
            else:
                new_children.append(elem)
        
        # Add all drawable elements grouped by color
        for color in color_order:
            for elem in color_groups.get(color, []):
                new_children.append(elem)
        
        root[:] = new_children

        # Persist the temp file in local storage tmp so it doesn't clutter projects.
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tag = generation_tag or str(int(time.time()))
        sorted_path = tmp_dir / f"{svg_path.stem}_{tag}.svg"
        tree.write(sorted_path, encoding="utf-8", xml_declaration=True)
        return sorted_path, color_metadata
    except Exception:
        logger.warning("SVG color sort failed, using original file", exc_info=True)
        return svg_path, color_metadata


def build_vpype_config_content(
    servo_delay_ms: float = 100.0,
    pen_debounce_steps: int = 7,
) -> str:
    """Generate vpype config content using current plotter gcode settings."""
    gcode = _get_default_gcode_settings()
    pen_up = getattr(gcode, "pen_up_command", "M280 P0 S110")
    if pen_up is None:
        pen_up = "M280 P0 S110"
    pen_down = getattr(gcode, "pen_down_command", "M280 P0 S130")
    if pen_down is None:
        pen_down = "M280 P0 S130"
    if servo_delay_ms is None:
        servo_delay_ms = 100.0
    if pen_debounce_steps is None or pen_debounce_steps < 1:
        pen_debounce_steps = 1
    
    # Extract servo angles from commands
    import re
    def extract_servo_angle(cmd: str) -> Optional[float]:
        """Extract S value from M280 command (e.g., 'M280 P0 S110' -> 110.0)."""
        match = re.search(r'S([\d.]+)', cmd)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def generate_exponential_pen_down_sequence(pen_up_cmd: str, pen_down_cmd: str, num_steps: int = 7) -> str:
        """
        Generate multiple M280 commands that exponentially approach pen_down value.
        This reduces bouncing by gradually lowering the pen instead of one sudden move.
        
        Args:
            pen_up_cmd: Command for pen up (e.g., "M280 P0 S110")
            pen_down_cmd: Command for pen down (e.g., "M280 P0 S130")
            num_steps: Total number of moves (default 7)
        
        Returns:
            Multi-line string with M280 commands and final delay
        """
        pen_up_angle = extract_servo_angle(pen_up_cmd)
        pen_down_angle = extract_servo_angle(pen_down_cmd)
        
        if pen_up_angle is None or pen_down_angle is None:
            # Fallback: if we can't parse angles, just use the original command with delay
            return f"{pen_down_cmd}\nG4 P{int(servo_delay_ms)}"
        
        # Extract command prefix (e.g., "M280 P0" from "M280 P0 S110")
        prefix_match = re.match(r'^([^S]+)', pen_down_cmd)
        if prefix_match:
            cmd_prefix = prefix_match.group(1).strip()
        else:
            cmd_prefix = "M280 P0"
        
        # Generate exponential approach: each step covers 50% of remaining distance
        # Formula: angle = pen_up + (pen_down - pen_up) * (1 - 0.5^step)
        # For num_steps=7: steps 1-6 are intermediate, step 7 is exact pen_down
        commands = []
        for step in range(1, num_steps):
            # Exponential approach: step 1 covers 50%, step 2 covers 75%, etc.
            progress = 1 - (0.5 ** step)
            angle = pen_up_angle + (pen_down_angle - pen_up_angle) * progress
            commands.append(f"{cmd_prefix} S{angle:.2f}")
        
        # Final step: exact pen_down value
        commands.append(f"{cmd_prefix} S{pen_down_angle:.2f}")
        
        # Add delay after final command
        commands.append(f"G4 P{int(servo_delay_ms)}")
        return "\n".join(commands)
    
    pen_down_sequence = generate_exponential_pen_down_sequence(pen_up, pen_down, num_steps=pen_debounce_steps)
    
    before_print = getattr(gcode, "before_print", None)
    if before_print is None:
        before_print = []
    # Ensure pen is up in document_start and include only pre-print sequence
    # Replace pen_down commands in before_print with exponential sequence
    doc_start_lines = []
    for line in before_print:
        if line.strip() == pen_down.strip():
            # Replace single pen_down with exponential sequence
            doc_start_lines.append(pen_down_sequence)
        else:
            doc_start_lines.append(line)
    # Check if pen_up is already in the lines
    pen_up_in_lines = any(line.strip().startswith(pen_up.strip()) for line in doc_start_lines)
    if not pen_up_in_lines:
        doc_start_lines.append(pen_up)  # No delay for pen up
    document_start = "\n".join(doc_start_lines)

    return textwrap.dedent(
        f'''# vpype/vpype-gcode profile for PolarVortex plotter
[gwrite.polarvortex]
# Work in millimeters for Marlin-style controllers
unit = "mm"

# Initial setup: absolute coords, mm units, and pen up
document_start = """
{document_start}
"""

# Ensure pen is raised between collections
linecollection_start = "{pen_up}\\n"

# First segment in a path: move then pen down (exponential approach to reduce bouncing)
segment_first = """
G0 X{{x:.3f}} Y{{y:.3f}}
{pen_down_sequence}
"""

# Subsequent segments while drawing
segment = "G1 X{{x:.3f}} Y{{y:.3f}} F1500\\n"

# Last segment in a path: finish move then pen up
segment_last = """
G1 X{{x:.3f}} Y{{y:.3f}} F1500
{pen_up}
"""

# Wrap up program with pen up
document_end = """
{pen_up} ; ensure pen up
M2 ; program end
"""
'''
    )


def ensure_vpype_config(
    path: Path = DEFAULT_VPYPE_CONFIG,
    servo_delay_ms: float = 100.0,
    pen_debounce_steps: int = 7,
) -> Path:
    """Ensure vpype config exists and reflects current plotter G-code settings.
    
    Args:
        path: Path to vpype config file
        servo_delay_ms: Delay in milliseconds after pen down
        pen_debounce_steps: Number of M280 commands for exponential pen down
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = build_vpype_config_content(servo_delay_ms=servo_delay_ms, pen_debounce_steps=pen_debounce_steps)
        needs_write = True
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
                needs_write = existing != content
            except Exception:
                needs_write = True
        if needs_write:
            path.write_text(content, encoding="utf-8")
    except Exception:
        logger.error("Failed to ensure vpype config at %s", path, exc_info=True)
    return path


OriginMode = Literal["lower_left", "center"]


def insert_m0_pen_changes(
    gcode_content: str,
    sorted_svg_path: Path,
    color_metadata: Dict[str, Any],
) -> str:
    """
    Insert M0 pause commands with color descriptors at color change boundaries.
    
    Args:
        gcode_content: Generated G-code content from vpype
        sorted_svg_path: Path to the sorted SVG file
        color_metadata: Metadata dict with color_order, color_count, color_descriptors
        
    Returns:
        Modified G-code content with M0 commands inserted
    """
    # If single color or no colors, no M0 needed
    color_order = color_metadata.get("color_order", [])
    color_count = color_metadata.get("color_count", 0)
    color_descriptors = color_metadata.get("color_descriptors", {})
    
    if color_count <= 1:
        return gcode_content
    
    # Filter out "none" colors from the order (they don't need pen changes)
    valid_colors = [c for c in color_order if c.lower() != "none"]
    if len(valid_colors) <= 1:
        return gcode_content
    
    # Parse sorted SVG to get exact color order as paths appear
    svg_color_order = _parse_sorted_svg_colors(sorted_svg_path)
    if not svg_color_order:
        # Fallback to metadata color order
        svg_color_order = valid_colors
    
    # Filter SVG color order to remove "none"
    svg_color_order = [c for c in svg_color_order if c.lower() != "none"]
    if len(svg_color_order) <= 1:
        return gcode_content
    
    lines = gcode_content.split("\n")
    result_lines = []
    
    # Get pen_up command to identify collection starts
    gcode_settings = _get_default_gcode_settings()
    pen_up = getattr(gcode_settings, "pen_up_command", "M280 P0 S110")
    if pen_up is None:
        pen_up = "M280 P0 S110"
    
    # Extract pen_up command prefix (e.g., "M280" from "M280 P0 S110")
    pen_up_prefix = pen_up.split()[0] if pen_up.split() else pen_up
    pen_up_normalized = pen_up.strip()
    
    # Track collection starts
    # Collection starts (linecollection_start) are pen_up commands that appear:
    # - On their own line (not part of segment_last multiline block)
    # - After we've seen at least one drawing command (G0/G1)
    # - segment_last has format: "G1 X... Y... F1500\n{pen_up}" (pen_up on next line)
    # - document_start pen_up appears BEFORE any G0/G1 commands
    
    collection_count = 0
    seen_drawing_commands = False  # Track if we've seen any G0/G1 commands yet
    pending_collection_start = False  # Track if we just saw a collection start pen_up
    in_collection = False  # Track if we're currently inside a color collection (to avoid M0 for subsequent paths)
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Check if this is a drawing command (G0 or G1)
        if line_stripped.startswith("G0") or line_stripped.startswith("G1"):
            seen_drawing_commands = True
            
            # If this is a G0 and we have a pending collection start, insert M0 before it
            # Only insert M0 for the FIRST G0 of a new color collection, not for subsequent paths
            if line_stripped.startswith("G0") and pending_collection_start and not in_collection:
                # This is the first G0 of a new color collection
                # collection_count = 0: first color (insert M0 for svg_color_order[0])
                # collection_count = 1: second color (insert M0 for svg_color_order[1])
                # collection_count = 2: third color (insert M0 for svg_color_order[2])
                # Insert M0 for all colors including the first (to ensure proper pen is loaded)
                if collection_count < len(svg_color_order):
                    # Insert M0 with color descriptor before the G0
                    # collection_count indexes the color we're starting
                    color_value = svg_color_order[collection_count]
                    color_desc = color_descriptors.get(color_value, _generate_color_descriptor(color_value))
                    m0_command = f"M0 {color_desc} ; Pen change for new color"
                    result_lines.append(m0_command)
                # Increment after using collection_count to index the color
                collection_count += 1
                pending_collection_start = False
                in_collection = True  # Mark that we're now inside a color collection
        
        # Check if this line contains pen_up command
        # Collection start pen_up appears standalone (linecollection_start)
        # Path end pen_up appears after G1 in segment_last (G1 on previous line)
        # document_start pen_up appears before any G0/G1 commands
        is_collection_start = False
        
        if pen_up_prefix in line_stripped or pen_up_normalized in line_stripped:
            # Check if this is document_start pen_up vs first linecollection_start pen_up
            # Both appear before G0/G1, but we need to distinguish them
            if not seen_drawing_commands:
                # Look ahead to see if next non-empty line is G0
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1
                
                if next_idx < len(lines):
                    next_line = lines[next_idx].strip()
                    if next_line.startswith("G0"):
                        # Next line is G0, so this is the first linecollection_start (collection start)
                        is_collection_start = True
                    else:
                        # Next line is not G0 (probably G90, G21, etc.), so this is document_start pen_up
                        is_collection_start = False
                else:
                    # No next line, treat as document_start
                    is_collection_start = False
            else:
                # After drawing has started, check if this is a collection start
                # Pattern analysis:
                # - segment_last: G1 ... F1500, then M280 (path end pen_up) - pen_up immediately after G1
                # - linecollection_start: M280 (collection start pen_up), then G0 ... (first segment of next path)
                # So: if previous line is G1, this is path end (segment_last)
                #     if next line is G0, this is collection start (linecollection_start)
                
                # Look at previous non-empty line
                prev_idx = i - 1
                while prev_idx >= 0 and not lines[prev_idx].strip():
                    prev_idx -= 1
                
                # Look at next non-empty line
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1
                
                if prev_idx >= 0:
                    prev_line = lines[prev_idx].strip()
                    if prev_line.startswith("G1"):
                        # Previous line is G1, so this pen_up is part of segment_last (path end)
                        # UNLESS the next line is G0, which means this is actually a collection start
                        if next_idx < len(lines):
                            next_line = lines[next_idx].strip()
                            if next_line.startswith("G0"):
                                # Next line is G0, so this is a collection start (linecollection_start)
                                is_collection_start = True
                            else:
                                # Next line is not G0, so this is path end
                                is_collection_start = False
                        else:
                            # No next line, treat as path end
                            is_collection_start = False
                    else:
                        # Previous line is not G1, check if next line is G0
                        if next_idx < len(lines):
                            next_line = lines[next_idx].strip()
                            if next_line.startswith("G0"):
                                # Next line is G0, so this is a collection start
                                is_collection_start = True
                            else:
                                # Next line is not G0, might be path end or something else
                                # If previous was also pen_up, it's likely collection start
                                if pen_up_prefix in prev_line or pen_up_normalized in prev_line:
                                    is_collection_start = True
                                else:
                                    is_collection_start = False
                        else:
                            # No next line, if previous was pen_up, treat as collection start
                            if pen_up_prefix in prev_line or pen_up_normalized in prev_line:
                                is_collection_start = True
                            else:
                                is_collection_start = False
                else:
                    # No previous line, check if next is G0
                    if next_idx < len(lines):
                        next_line = lines[next_idx].strip()
                        if next_line.startswith("G0"):
                            is_collection_start = True
                        else:
                            is_collection_start = False
                    else:
                        is_collection_start = False
        
        # If this is a collection start pen_up, mark it as pending (M0 will be inserted before next G0)
        if is_collection_start:
            pending_collection_start = True
            in_collection = False  # Reset - we're starting a new color collection
        
        # Add the current line to result
        result_lines.append(line)
        
        i += 1
    
    return "\n".join(result_lines)


def _parse_sorted_svg_colors(sorted_svg_path: Path) -> list:
    """
    Parse sorted SVG to extract color order of drawable elements.
    
    Returns list of stroke values in order they appear in the sorted SVG.
    """
    try:
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(sorted_svg_path)
        root = tree.getroot()
        
        drawable_tags = {
            "path",
            "line",
            "polyline",
            "polygon",
            "rect",
            "circle",
            "ellipse",
        }
        
        color_order = []
        last_color = None
        
        for child in root:
            tag = child.tag.rsplit("}", 1)[-1] if "}" in child.tag else child.tag
            if tag in drawable_tags:
                stroke = _get_stroke_value(child)
                if stroke != last_color:
                    color_order.append(stroke)
                    last_color = stroke
                    
        return color_order
    except Exception:
        logger.warning("Failed to parse sorted SVG colors", exc_info=True)
        return []


def _dbg_log(hypothesis: str, location: str, message: str, data: Optional[dict] = None, run_id: str = "pre-fix"):
    """Append a tiny NDJSON log for debug mode."""
    payload = {
        "sessionId": "debug-session",
        "runId": run_id,
        "hypothesisId": hypothesis,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        # Avoid breaking main flow if logging fails
        logger.debug("debug log write failed", exc_info=True)


def build_vpype_pipeline(
    svg_path: Path,
    paper_width_mm: float,
    paper_height_mm: float,
    output_path: Path,
    config_path: Optional[Path] = DEFAULT_VPYPE_CONFIG,
    profile: str = DEFAULT_GWRITE_PROFILE,
    origin_mode: OriginMode = "lower_left",
    rotate_90: bool = False,
    generation_tag: Optional[str] = None,  # not used here; kept for signature parity
    enable_occult: bool = False,
    occult_ignore_layers: bool = False,
    occult_across_layers_only: bool = False,
    occult_keep_occulted: bool = False,
    enable_optimization: bool = False,
    linemerge_tolerance: float = 0.5,
    linesimplify_tolerance: float = 0.1,
    reloop_tolerance: float = 0.1,
    linesort_enabled: bool = True,
    linesort_two_opt: bool = True,
    linesort_passes: int = 250,
    servo_delay_ms: float = 100.0,
    pen_debounce_steps: int = 7,
) -> str:
    """Build a vpype pipeline string for SVG->G-code conversion."""
    width, height = float(paper_width_mm), float(paper_height_mm)
    # Always scale to the selected page size and center on the page.
    place_cmd = f"layout --fit-to-margins 0 {width}mmx{height}mm"

    # Coordinate alignment: flip Y while keeping X unchanged.
    # - Center origin: move page center to (0,0), then flip Y about that origin.
    # - Lower-left origin: flip Y around top-left and translate back down.
    if origin_mode == "center":
        flip_cmds = [
            f"translate -- {-width / 2:.3f}mm {-height / 2:.3f}mm",
            "scale -- 1 -1",
        ]
    else:
        flip_cmds = [
            "scale -- 1 -1",
            f"translate 0mm {height:.3f}mm",
        ]

    # vpype-gcode plugin provides `gwrite` for G-code export
    # Commands in vpype are space-separated (no shell pipes needed)
    # Prefer local stored vpype config/profile for consistent pen control
    config_arg = ""
    if config_path:
        ensure_vpype_config(config_path, servo_delay_ms=servo_delay_ms, pen_debounce_steps=pen_debounce_steps)
        if config_path.exists():
            config_arg = f'--config "{config_path}" '
        else:
            logger.warning("vpype config not found at %s, falling back to defaults", config_path)

    # Build occult command if enabled
    occult_cmd = ""
    if enable_occult:
        occult_flags = []
        # -a flag overrides -i flag (per occult documentation)
        if occult_across_layers_only:
            occult_flags.append("-a")
        elif occult_ignore_layers:
            occult_flags.append("-i")
        if occult_keep_occulted:
            occult_flags.append("-k")
        
        occult_flag_str = " ".join(occult_flags)
        occult_cmd = f"occult {occult_flag_str}".strip()

    # Build optimization commands if enabled
    optimization_cmds = []
    if enable_optimization:
        optimization_cmds.append(f"linemerge --tolerance {linemerge_tolerance:.3f}mm")
        optimization_cmds.append(f"linesimplify --tolerance {linesimplify_tolerance:.3f}mm")
        optimization_cmds.append(f"reloop --tolerance {reloop_tolerance:.3f}mm")
        if linesort_enabled:
            if linesort_two_opt:
                optimization_cmds.append(f"linesort --two-opt --passes {linesort_passes}")
            else:
                optimization_cmds.append(f"linesort --passes {linesort_passes}")
    optimization_cmd_str = " ".join(optimization_cmds)

    pipeline_parts = [
        config_arg,
        f'read "{svg_path}"',
        occult_cmd,
        optimization_cmd_str,
        "rotate -- -90deg" if rotate_90 else "",
        place_cmd,
        *flip_cmds,
    ]
    pipeline_parts.append(f'gwrite --profile {profile} "{output_path}"')

    return " ".join(part for part in pipeline_parts if part)


async def run_vpype_pipeline(pipeline: str) -> None:
    """Run vpype as subprocess with the given pipeline string."""
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:53", "run_vpype_pipeline start", {"pipeline": pipeline})
    # #endregion
    # Split respecting quotes so paths remain intact
    args = ["vpype", *shlex.split(pipeline)]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:63", "run_vpype_pipeline completed", {"returncode": proc.returncode, "stderr": stderr.decode("utf-8", errors="ignore")})
    # #endregion
    if proc.returncode != 0:
        logger.error("vpype failed: %s", stderr.decode("utf-8", errors="ignore"))
        raise RuntimeError(f"vpype failed: {stderr.decode('utf-8', errors='ignore')}")
    if stdout:
        logger.info("vpype output: %s", stdout.decode("utf-8", errors="ignore"))


async def convert_svg_to_gcode_file(
    svg_path: Path,
    output_path: Path,
    paper_width_mm: float,
    paper_height_mm: float,
    pen_mapping: Optional[str] = None,  # reserved for future use
    origin_mode: OriginMode = "lower_left",
    rotate_90: bool = False,
    generation_tag: Optional[str] = None,
    suppress_m0: bool = False,
    enable_occult: bool = False,
    occult_ignore_layers: bool = False,
    occult_across_layers_only: bool = False,
    occult_keep_occulted: bool = False,
    enable_optimization: bool = False,
    linemerge_tolerance: float = 0.5,
    linesimplify_tolerance: float = 0.1,
    reloop_tolerance: float = 0.1,
    linesort_enabled: bool = True,
    linesort_two_opt: bool = True,
    linesort_passes: int = 250,
    servo_delay_ms: float = 100.0,
    pen_debounce_steps: int = 7,
) -> None:
    """Convert SVG to G-code using vpype CLI."""
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:79", "convert_svg_to_gcode_file start", {
        "svg_path": str(svg_path),
        "output_path": str(output_path),
        "paper_width_mm": paper_width_mm,
        "paper_height_mm": paper_height_mm,
        "pen_mapping": pen_mapping,
        "origin_mode": origin_mode,
        "rotate_90": rotate_90,
        "enable_occult": enable_occult,
    })
    # #endregion
    sorted_svg_path, color_metadata = sort_svg_by_stroke(svg_path, generation_tag=generation_tag)
    cleanup_sorted = sorted_svg_path != svg_path

    try:
        pipeline = build_vpype_pipeline(
            svg_path=sorted_svg_path,
            paper_width_mm=paper_width_mm,
            paper_height_mm=paper_height_mm,
            output_path=output_path,
            config_path=DEFAULT_VPYPE_CONFIG,
            profile=DEFAULT_GWRITE_PROFILE,
            origin_mode=origin_mode,
            rotate_90=rotate_90,
            generation_tag=generation_tag,
            enable_occult=enable_occult,
            occult_ignore_layers=occult_ignore_layers,
            occult_across_layers_only=occult_across_layers_only,
            occult_keep_occulted=occult_keep_occulted,
            enable_optimization=enable_optimization,
            linemerge_tolerance=linemerge_tolerance,
            linesimplify_tolerance=linesimplify_tolerance,
            reloop_tolerance=reloop_tolerance,
            linesort_enabled=linesort_enabled,
            linesort_two_opt=linesort_two_opt,
            linesort_passes=linesort_passes,
            servo_delay_ms=servo_delay_ms,
            pen_debounce_steps=pen_debounce_steps,
        )
        await run_vpype_pipeline(pipeline)

        # Post-process G-code to insert M0 pen change commands (unless suppressed)
        if not suppress_m0:
            try:
                gcode_content = output_path.read_text(encoding="utf-8", errors="ignore")
                gcode_content = insert_m0_pen_changes(gcode_content, sorted_svg_path, color_metadata)
                output_path.write_text(gcode_content, encoding="utf-8")
            except Exception:
                logger.debug("Failed to insert M0 pen changes", exc_info=True)

        # Prepend metadata comments to the generated G-code file.
        try:
            header_lines = [
                f"; Generated by PolarVortex v{APP_VERSION}",
                f"; Generated at: {generation_tag or int(time.time())}",
                f"; Source SVG: {svg_path.name}",
                f"; Paper size (mm): {paper_width_mm} x {paper_height_mm}",
                f"; Origin mode: {origin_mode}",
                f"; Rotate 90 CW: {rotate_90}",
            ]
            if pen_mapping:
                header_lines.append(f"; Pen mapping: {pen_mapping}")
            # Add color count info if multicolor
            color_count = color_metadata.get("color_count", 0)
            if color_count > 1:
                header_lines.append(f"; Colors: {color_count} unique colors detected")
            # Add note if M0 color changes are suppressed
            if suppress_m0:
                header_lines.append(f"; M0 color change commands disabled - printing in one color")
            # Add occult info if enabled
            if enable_occult:
                occult_flags = []
                if occult_across_layers_only:
                    occult_flags.append("across-layers-only")
                elif occult_ignore_layers:
                    occult_flags.append("ignore-layers")
                if occult_keep_occulted:
                    occult_flags.append("keep-occulted")
                occult_info = "occult enabled"
                if occult_flags:
                    occult_info += f" ({', '.join(occult_flags)})"
                header_lines.append(f"; Hidden line removal: {occult_info}")
            # Add pen debounce info (including sequence for verification)
            header_lines.append(
                f"; Pen debounce: steps={pen_debounce_steps}, delay_ms={servo_delay_ms:.0f}"
            )
            pen_sequence_lines = pen_down_sequence.split("\n")
            for line in pen_sequence_lines:
                header_lines.append(f"; Pen debounce cmd: {line}")
            # Add optimization info if enabled
            if enable_optimization:
                opt_parts = []
                opt_parts.append(f"linemerge={linemerge_tolerance:.3f}mm")
                opt_parts.append(f"linesimplify={linesimplify_tolerance:.3f}mm")
                opt_parts.append(f"reloop={reloop_tolerance:.3f}mm")
                if linesort_enabled:
                    sort_info = f"linesort(passes={linesort_passes}"
                    if linesort_two_opt:
                        sort_info += ",two-opt"
                    sort_info += ")"
                    opt_parts.append(sort_info)
                opt_info = "optimization enabled"
                if opt_parts:
                    opt_info += f" ({', '.join(opt_parts)})"
                header_lines.append(f"; G-code optimization: {opt_info}")
            header = "\n".join(header_lines) + "\n"
            original = output_path.read_text(encoding="utf-8", errors="ignore")
            output_path.write_text(header + original, encoding="utf-8")
        except Exception:
            logger.debug("Failed to write G-code metadata header", exc_info=True)

        # Clean up the temp colorsorted file if we created one (after subprocess fully completed).
        if cleanup_sorted and sorted_svg_path.exists():
            try:
                sorted_svg_path.unlink()
            except Exception:
                logger.debug("Failed to delete temp colorsorted SVG %s", sorted_svg_path, exc_info=True)
    finally:
        # Leave the temp file on failure for debugging.
        pass
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:91", "convert_svg_to_gcode_file done", {"output_exists": output_path.exists()})
    # #endregion

