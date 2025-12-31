import asyncio
import json
import logging
import shlex
import time
import textwrap
from pathlib import Path
from typing import Dict, Literal, Optional

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


def sort_svg_by_stroke(
    svg_path: Path,
    tmp_dir: Path = Path("/app/local_storage/tmp"),
    generation_tag: Optional[str] = None,
) -> Path:
    """
    Reorder drawable SVG elements so they are grouped by stroke color.

    This ensures plotting is done one color at a time before switching pens.
    """
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

        original_children = list(root)
        preserved = []
        color_order = []
        color_groups: Dict[str, list] = {}

        for child in original_children:
            tag = child.tag.rsplit("}", 1)[-1] if "}" in child.tag else child.tag
            if tag in drawable_tags:
                stroke = _get_stroke_value(child)
                if stroke not in color_order:
                    color_order.append(stroke)
                color_groups.setdefault(stroke, []).append(child)
            else:
                preserved.append(child)

        # If nothing to sort, return original
        if not color_order:
            return svg_path

        # Rebuild child list: keep preserved elements, then grouped drawables by stroke order
        new_children = preserved + [
            elem for color in color_order for elem in color_groups.get(color, [])
        ]
        root[:] = new_children

        # Persist the temp file in local storage tmp so it doesn't clutter projects.
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tag = generation_tag or str(int(time.time()))
        sorted_path = tmp_dir / f"{svg_path.stem}_{tag}.svg"
        tree.write(sorted_path, encoding="utf-8", xml_declaration=True)
        return sorted_path
    except Exception:
        logger.warning("SVG color sort failed, using original file", exc_info=True)
        return svg_path


def build_vpype_config_content() -> str:
    """Generate vpype config content using current plotter gcode settings."""
    gcode = _get_default_gcode_settings()
    pen_up = getattr(gcode, "pen_up_command", "M280 P0 S110")
    if pen_up is None:
        pen_up = "M280 P0 S110"
    pen_down = getattr(gcode, "pen_down_command", "M280 P0 S130")
    if pen_down is None:
        pen_down = "M280 P0 S130"
    before_print = getattr(gcode, "before_print", None)
    if before_print is None:
        before_print = []
    # Ensure pen is up in document_start and include only pre-print sequence
    doc_start_lines = [*before_print]
    if pen_up not in doc_start_lines:
        doc_start_lines.append(pen_up)
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

# First segment in a path: move then pen down
segment_first = """
G0 X{{x:.3f}} Y{{y:.3f}}
{pen_down}
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


def ensure_vpype_config(path: Path = DEFAULT_VPYPE_CONFIG) -> Path:
    """Ensure vpype config exists and reflects current plotter G-code settings."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = build_vpype_config_content()
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
        ensure_vpype_config(config_path)
        if config_path.exists():
            config_arg = f'--config "{config_path}" '
        else:
            logger.warning("vpype config not found at %s, falling back to defaults", config_path)

    pipeline_parts = [
        config_arg,
        f'read "{svg_path}"',
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
    })
    # #endregion
    sorted_svg_path = sort_svg_by_stroke(svg_path, generation_tag=generation_tag)

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
        )
        await run_vpype_pipeline(pipeline)

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
            header = "\n".join(header_lines) + "\n"
            original = output_path.read_text(encoding="utf-8", errors="ignore")
            output_path.write_text(header + original, encoding="utf-8")
        except Exception:
            logger.debug("Failed to write G-code metadata header", exc_info=True)
    finally:
        # Clean up the temp colorsorted file if we created one.
        try:
            if sorted_svg_path != svg_path and sorted_svg_path.exists():
                sorted_svg_path.unlink()
        except Exception:
            logger.debug("Failed to delete temp colorsorted SVG %s", sorted_svg_path, exc_info=True)
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:91", "convert_svg_to_gcode_file done", {"output_exists": output_path.exists()})
    # #endregion

