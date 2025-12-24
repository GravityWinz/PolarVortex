import asyncio
import json
import logging
import shlex
import time
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)
LOG_PATH = Path(r"c:\Users\mlutz\OneDrive\Desktop\Cursor\PolarVortex\.cursor\debug.log")

PaperSize = Literal["A4", "Letter", "A3"]
FitMode = Literal["fit", "center"]

PAPER_DIMENSIONS_MM = {
    "A4": (210.0, 297.0),
    "Letter": (215.9, 279.4),
    "A3": (297.0, 420.0),
}


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


def build_vpype_pipeline(svg_path: Path, paper: PaperSize, fit_mode: FitMode, output_path: Path) -> str:
    """Build a vpype pipeline string for SVG->G-code conversion."""
    width, height = PAPER_DIMENSIONS_MM.get(paper, PAPER_DIMENSIONS_MM["A4"])
    # `layout` keeps things centered by default. With `--fit-to-margins 0` it
    # scales uniformly to fit the page, avoiding the deprecated/invalid
    # `--origin` flag we previously passed to `scaleto`.
    if fit_mode == "fit":
        place_cmd = f"layout --fit-to-margins 0 {width}mmx{height}mm"
    else:
        place_cmd = f"layout {width}mmx{height}mm"

    # vpype-gcode plugin provides `gwrite` for G-code export
    # Commands in vpype are space-separated (no shell pipes needed)
    pipeline = (
        f'read "{svg_path}" '
        f"{place_cmd} "
        f'gwrite --profile gcode \"{output_path}\"'
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
    paper: PaperSize = "A4",
    fit_mode: FitMode = "fit",
    pen_mapping: Optional[str] = None,  # reserved for future use
) -> None:
    """Convert SVG to G-code using vpype CLI."""
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:79", "convert_svg_to_gcode_file start", {
        "svg_path": str(svg_path),
        "output_path": str(output_path),
        "paper": paper,
        "fit_mode": fit_mode,
        "pen_mapping": pen_mapping,
    })
    # #endregion
    pipeline = build_vpype_pipeline(svg_path, paper, fit_mode, output_path)
    await run_vpype_pipeline(pipeline)
    # #region agent log
    _dbg_log("H1", "vpype_converter.py:91", "convert_svg_to_gcode_file done", {"output_exists": output_path.exists()})
    # #endregion

