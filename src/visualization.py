"""
Generate SVG visualizations from feedback log JSONs: heatmap (count per cell across files)
and intersection (cells selected in all files of the best combination).
"""

from typing import Any
from pathlib import Path
import os
import tempfile
import xml.etree.ElementTree as ET

from svgutils.compose import Figure, Panel, SVG

def _get_point_sets_and_geometry(
    loaded_jsons: dict,
) -> tuple[dict[str, set], float, float, float, float, str]:
    """
    Extract point sets and geometry from loaded_jsons.

    Returns (point_sets, seg_w, seg_h, image_w, image_h, image_path).
    Uses the first file's feedbackLocation as the canonical geometry, assuming
    consistency has already been checked in the API layer.
    """
    point_sets: dict[str, set] = {}
    seg_w = seg_h = 1.0
    image_w = image_h = 1.0
    image_path = ""
    first = True

    for file_id, log_data in loaded_jsons.items():
        fl = log_data["feedbackLocation"]
        w = fl["segment_size_px"]["w"]
        h = fl["segment_size_px"]["h"]

        if first:
            seg_w, seg_h = float(w), float(h)
            img_size = fl.get("image_size") or {}
            image_w = float(img_size.get("w", seg_w))
            image_h = float(img_size.get("h", seg_h))
            image_path = str(fl.get("image_path", ""))
            first = False

        rows = fl["chosenPoints"]["row"]
        cols = fl["chosenPoints"]["col"]
        points = set(zip(rows, cols))
        point_sets[file_id] = points

    if not point_sets:
        return point_sets, seg_w, seg_h, image_w, image_h, image_path

    return point_sets, seg_w, seg_h, image_w, image_h, image_path


def _count_per_cell(point_sets: dict[str, set]) -> dict[tuple[int, int], int]:
    """For each (row, col) that appears in any file, count how many files contain it."""
    counts: dict[tuple[int, int], int] = {}
    for points in point_sets.values():
        for p in points:
            counts[p] = counts.get(p, 0) + 1
    return counts


def _intersection_points(point_sets: dict[str, set], file_ids: tuple[str, ...] | None) -> set[tuple[int, int]]:
    """Intersection of chosen points across the given file_ids. If file_ids is None, use all."""
    if not point_sets:
        return set()
    ids = file_ids or list(point_sets.keys())
    if not ids:
        return set()
    result = set(point_sets[ids[0]])
    for fid in ids[1:]:
        result &= point_sets[fid]
    return result


def _rgb_interpolate(t: float) -> str:
    """t in [0, 1]. Light blue (low) -> dark blue (high)."""
    t = max(0.0, min(1.0, t))
    r = int(240 * (1 - t) + 33 * t)
    g = int(248 * (1 - t) + 150 * t)
    b = int(255 * (1 - t) + 243 * t)
    return f"rgb({r},{g},{b})"

def _compose_with_background(
    background_path: Path,
    overlay_svg: str,
    width: float,
    height: float,
) -> str:
    """
    Use svgutils.compose to layer the original SVG (background_path)
    and the overlay SVG string into a single SVG figure, scaling the
    background so its coordinate system matches the overlay's width/height.
    """
    # Determine intrinsic size of the background SVG to compute a scale factor
    try:
        root = ET.parse(background_path).getroot()
        orig_w = float(root.get("width", str(width)))
        orig_h = float(root.get("height", str(height)))
    except Exception:
        orig_w, orig_h = width, height

    sx = width / orig_w if orig_w else 1.0
    sy = height / orig_h if orig_h else 1.0

    bg = SVG(str(background_path)).scale(sx, sy)

    # svgutils.compose.SVG expects a filename, not raw SVG content.
    # Write the overlay SVG to a temporary file and load it from there.
    tmp_file = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    try:
        tmp_file.write(overlay_svg.encode("utf-8"))
        tmp_file.flush()
        tmp_path = tmp_file.name
    finally:
        tmp_file.close()

    try:
        ov = SVG(tmp_path)
        fig = Figure(str(width), str(height),
                     Panel(bg).move(0, 0),
                     Panel(ov).move(0, 0))
        out = fig.tostr()
        return out.decode("utf-8") if isinstance(out, bytes) else str(out)
    finally:
        # Clean up the temporary overlay file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

def render_heatmap_svg(loaded_jsons: dict[str, Any], include_original: bool) -> str:
    """
    Build an SVG heatmap: each cell is colored by how many files selected it (0 = not drawn, max = darkest).
    Uses segment_size_px from the first file and a bounding box of all chosen points.
    """
    if not loaded_jsons:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    point_sets, seg_w, seg_h, image_w, image_h, image_path = _get_point_sets_and_geometry(loaded_jsons)
    if not point_sets:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    counts = _count_per_cell(point_sets)
    max_count = max(counts.values()) if counts else 1
    width = image_w
    height = image_h

    rects = []
    for (r, c), count in sorted(counts.items()):
        t = count / max_count if max_count else 0
        fill = _rgb_interpolate(t)
        x = c * seg_w
        y = r * seg_h
        rects.append(
            f'<rect x="{x}" y="{y}" width="{seg_w}" height="{seg_h}" '
            f'fill="{fill}" fill-opacity="0.6" stroke="#333" stroke-width="0.25"/>'
        )

    body = "\n".join(rects)
    overlay_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<g>{body}</g></svg>'
    )

    if include_original and image_path:
        images_dir = Path(os.environ.get("IMAGES_DIR", "/app/uploads"))
        bg_path = images_dir / image_path
        if bg_path.exists():
            return _compose_with_background(bg_path, overlay_svg, width, height)

    return overlay_svg


def render_intersection_svg(
    loaded_jsons: dict[str, Any],
    best_combination: tuple[str, ...] | None,
    include_original: bool,
) -> str:
    """
    Build an SVG of the intersection: only cells selected in every file of best_combination
    (or in all files if best_combination is None). Same grid geometry as heatmap.
    """
    if not loaded_jsons:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    point_sets, seg_w, seg_h, image_w, image_h, image_path = _get_point_sets_and_geometry(loaded_jsons)
    if not point_sets:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    inter = _intersection_points(point_sets, best_combination)

    width = image_w
    height = image_h

    rects = []
    for r, c in sorted(inter):
        x = c * seg_w
        y = r * seg_h
        rects.append(
            f'<rect x="{x}" y="{y}" width="{seg_w}" height="{seg_h}" '
            f'fill="steelblue" fill-opacity="0.6" stroke="#1a5276" stroke-width="0.25"/>'
        )

    body = "\n".join(rects)
    overlay_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<g>{body}</g></svg>'
    )

    if include_original and image_path:
        images_dir = Path(os.environ.get("IMAGES_DIR", "/app/uploads"))
        bg_path = images_dir / image_path
        if bg_path.exists():
            return _compose_with_background(bg_path, overlay_svg, width, height)

    return overlay_svg


def render_visualizations(
    loaded_jsons: dict[str, Any],
    best_combination: tuple[str, ...] | None,
    include_original: bool,
) -> dict[str, str]:
    """
    Produce heatmap and intersection SVGs from feedback logs.
    best_combination is the tuple of file_ids from stability (used for intersection).
    Returns {"heatmap_svg": "...", "intersection_svg": "..."}.
    """
    return {
        "heatmap_svg": render_heatmap_svg(loaded_jsons, include_original),
        "intersection_svg": render_intersection_svg(loaded_jsons, best_combination, include_original),
    }
