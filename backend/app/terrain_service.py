import asyncio
import math
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, Tuple

import httpx
import numpy as np
from PIL import Image

from .config_service import config_service
from .terrain_models import TerrainRidgelineRequest

TILE_SIZE = 512  # Using @2x tiles
MAPBOX_TILE_URL = (
    "https://api.mapbox.com/v4/mapbox.terrain-rgb/{z}/{x}/{y}@2x.pngraw?access_token={token}"
)


@dataclass
class PaperDimensions:
    width_mm: float
    height_mm: float
    name: str


def _get_mapbox_token() -> str:
    token = os.getenv("MAPBOX_TOKEN")
    if not token:
        raise RuntimeError("MAPBOX_TOKEN is not set")
    return token


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lonlat_to_tile_fraction(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _tile_range(min_lat: float, min_lon: float, max_lat: float, max_lon: float, zoom: int) -> Tuple[int, int, int, int]:
    x0, y0 = _lonlat_to_tile_fraction(max_lat, min_lon, zoom)
    x1, y1 = _lonlat_to_tile_fraction(min_lat, max_lon, zoom)
    min_x = int(math.floor(min(x0, x1)))
    max_x = int(math.floor(max(x0, x1)))
    min_y = int(math.floor(min(y0, y1)))
    max_y = int(math.floor(max(y0, y1)))
    n = 2**zoom
    min_x = max(0, min_x)
    min_y = max(0, min_y)
    max_x = min(n - 1, max_x)
    max_y = min(n - 1, max_y)
    return min_x, max_x, min_y, max_y


def _meters_per_pixel(lat: float, zoom: int) -> float:
    return 156543.03392 * math.cos(math.radians(lat)) / (2**zoom)


def _choose_zoom(req: TerrainRidgelineRequest) -> int:
    bbox = req.bbox
    width_m = 6378137.0 * math.radians(bbox.maxLon - bbox.minLon)
    target_spacing_m = width_m / max(req.cols - 1, 1)
    center_lat = (bbox.minLat + bbox.maxLat) / 2.0
    for zoom in range(14, -1, -1):
        if _meters_per_pixel(center_lat, zoom) <= target_spacing_m:
            return zoom
    return 0


async def _fetch_tile(
    client: httpx.AsyncClient,
    token: str,
    zoom: int,
    x: int,
    y: int,
    semaphore: asyncio.Semaphore,
) -> Tuple[Tuple[int, int], np.ndarray]:
    url = MAPBOX_TILE_URL.format(z=zoom, x=x, y=y, token=token)
    async with semaphore:
        resp = await client.get(url, timeout=30.0)
        resp.raise_for_status()
        image = Image.open(BytesIO(resp.content)).convert("RGB")
        return (x, y), np.array(image)


async def _load_tiles(
    zoom: int,
    min_x: int,
    max_x: int,
    min_y: int,
    max_y: int,
    token: str,
) -> Dict[Tuple[int, int], np.ndarray]:
    tiles: Dict[Tuple[int, int], np.ndarray] = {}
    semaphore = asyncio.Semaphore(6)
    async with httpx.AsyncClient() as client:
        tasks = [
            _fetch_tile(client, token, zoom, x, y, semaphore)
            for x in range(min_x, max_x + 1)
            for y in range(min_y, max_y + 1)
        ]
        for coro in asyncio.as_completed(tasks):
            (x, y), data = await coro
            tiles[(x, y)] = data
    return tiles


def _decode_elevation(pixel: np.ndarray) -> float:
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
    return -10000.0 + (r * 256 * 256 + g * 256 + b) * 0.1


def _project_x(lon: float) -> float:
    return 6378137.0 * math.radians(lon)


def _resolve_paper_dimensions(req: TerrainRidgelineRequest) -> PaperDimensions:
    papers = config_service.list_papers().papers
    target = None
    if req.paper_id:
        target = next((p for p in papers if p.id == req.paper_id), None)
    if not target and req.paper_size:
        target = next(
            (p for p in papers if p.paper_size.lower() == req.paper_size.lower()), None
        )
    if not target:
        target = next((p for p in papers if p.is_default), None)
    if not target and papers:
        target = papers[0]
    if not target:
        raise RuntimeError("No paper configurations available")
    return PaperDimensions(
        width_mm=float(target.width),
        height_mm=float(target.height),
        name=target.name or target.paper_size,
    )


async def generate_ridgeline_svg(req: TerrainRidgelineRequest) -> Tuple[str, PaperDimensions]:
    token = _get_mapbox_token()
    zoom = _choose_zoom(req)
    bbox = req.bbox
    min_x, max_x, min_y, max_y = _tile_range(
        bbox.minLat, bbox.minLon, bbox.maxLat, bbox.maxLon, zoom
    )
    tile_count = (max_x - min_x + 1) * (max_y - min_y + 1)
    if tile_count > 100:
        raise RuntimeError("Bounding box too large for terrain sampling; zoom in or reduce area.")
    tiles = await _load_tiles(zoom, min_x, max_x, min_y, max_y, token)

    paper = _resolve_paper_dimensions(req)
    width_mm = paper.width_mm
    height_mm = paper.height_mm

    x_min = _project_x(bbox.minLon)
    x_max = _project_x(bbox.maxLon)
    x_span = max(x_max - x_min, 1e-6)

    row_spacing = min(req.row_spacing, height_mm / max(req.rows - 1, 1))

    svg_lines: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}mm" height="{height_mm}mm" viewBox="0 0 {width_mm:.3f} {height_mm:.3f}">',
        f'<g fill="none" stroke="{req.stroke_color}" stroke-width="{req.stroke_width}" stroke-linecap="round" stroke-linejoin="round">',
    ]

    for row in range(req.rows):
        t_row = row / max(req.rows - 1, 1)
        lat = _lerp(bbox.maxLat, bbox.minLat, t_row)
        y_base = row * row_spacing
        points: List[str] = []
        for col in range(req.cols):
            t_col = col / max(req.cols - 1, 1)
            lon = _lerp(bbox.minLon, bbox.maxLon, t_col)
            xf, yf = _lonlat_to_tile_fraction(lat, lon, zoom)
            tile_x = int(math.floor(xf))
            tile_y = int(math.floor(yf))
            tile = tiles.get((tile_x, tile_y))
            if tile is None:
                elevation = 0.0
            else:
                px = int((xf - tile_x) * TILE_SIZE)
                py = int((yf - tile_y) * TILE_SIZE)
                px = min(max(px, 0), TILE_SIZE - 1)
                py = min(max(py, 0), TILE_SIZE - 1)
                elevation = _decode_elevation(tile[py, px])

            x_m = _project_x(lon)
            x_mm = (x_m - x_min) / x_span * width_mm
            y_mm = y_base - elevation * req.height_scale
            points.append(f"{x_mm:.2f},{y_mm:.2f}")

        if points:
            svg_lines.append(f'  <path d="M {points[0]} L {" ".join(points[1:])}" />')

    svg_lines.append("</g></svg>")
    return "\n".join(svg_lines), paper
