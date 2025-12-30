import asyncio
import json
import logging
import shlex
import time
import textwrap
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)
# Write debug logs inside the repo so paths work in containers and on host
# Persist vpype debug logs inside container storage
LOG_PATH = Path("/app/local_storage/log/vpype.log")
# Store vpype config in persistent local storage so it survives rebuilds
DEFAULT_VPYPE_CONFIG = Path("/app/local_storage/config/vpype.toml")
DEFAULT_GWRITE_PROFILE = "polarvortex"
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


def build_vpype_config_content() -> str:
    """Generate vpype config content using current plotter gcode settings."""
    gcode = _get_default_gcode_settings()
    pen_up = getattr(gcode, "pen_up_command", "M280 P0 S110") or "M280 P0 S110"
    pen_down = getattr(gcode, "pen_down_command", "M280 P0 S130") or "M280 P0 S130"
    before_print = getattr(gcode, "before_print", None) or []
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


FitMode = Literal["fit", "center"]


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
    fit_mode: FitMode,
    output_path: Path,
    config_path: Optional[Path] = DEFAULT_VPYPE_CONFIG,
    profile: str = DEFAULT_GWRITE_PROFILE,
) -> str:
    """Build a vpype pipeline string for SVG->G-code conversion."""
    width, height = float(paper_width_mm), float(paper_height_mm)
    # `layout` keeps things centered by default. With `--fit-to-margins 0` it
    # scales uniformly to fit the page, avoiding the deprecated/invalid
    # `--origin` flag we previously passed to `scaleto`.
    if fit_mode == "fit":
        place_cmd = f"layout --fit-to-margins 0 {width}mmx{height}mm"
    else:
        place_cmd = f"layout {width}mmx{height}mm"

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

    pipeline = (
        f"{config_arg}"
        f'read "{svg_path}" '
        f"{place_cmd} "
        f'gwrite --profile {profile} \"{output_path}\"'
    )
    return pipeline


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
    fit_mode: FitMode = "fit",
    pen_mapping: Optional[str] = None,  # reserved for future use
) -> None:
    """Convert SVG to G-code using vpype CLI."""
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:79", "convert_svg_to_gcode_file start", {
        "svg_path": str(svg_path),
        "output_path": str(output_path),
        "paper_width_mm": paper_width_mm,
        "paper_height_mm": paper_height_mm,
        "fit_mode": fit_mode,
        "pen_mapping": pen_mapping,
    })
    # #endregion
    pipeline = build_vpype_pipeline(
        svg_path=svg_path,
        paper_width_mm=paper_width_mm,
        paper_height_mm=paper_height_mm,
        fit_mode=fit_mode,
        output_path=output_path,
        config_path=DEFAULT_VPYPE_CONFIG,
        profile=DEFAULT_GWRITE_PROFILE,
    )
    await run_vpype_pipeline(pipeline)
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:91", "convert_svg_to_gcode_file done", {"output_exists": output_path.exists()})
    # #endregion

