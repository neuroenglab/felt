"""
Generate SVG visualizations from feedback log JSONs: heatmap (count per cell across files)
and intersection (cells selected in all files of the best combination).
"""

from typing import Any


def _get_point_sets_and_geometry(loaded_jsons: dict) -> tuple[dict[str, set], float, float, int, int, int, int]:
    """Extract point sets and grid geometry from loaded_jsons. Returns (point_sets, seg_w, seg_h, min_row, max_row, min_col, max_col)."""
    point_sets = {}
    seg_w, seg_h = 1.0, 1.0
    min_row = min_col = float("inf")
    max_row = max_col = float("-inf")

    for file_id, log_data in loaded_jsons.items():
        fl = log_data["feedbackLocation"]
        w = fl["segment_size_px"]["w"]
        h = fl["segment_size_px"]["h"]
        seg_w, seg_h = w, h

        rows = fl["chosenPoints"]["row"]
        cols = fl["chosenPoints"]["col"]
        points = set(zip(rows, cols))
        point_sets[file_id] = points

        for r, c in points:
            min_row = min(min_row, r)
            max_row = max(max_row, r)
            min_col = min(min_col, c)
            max_col = max(max_col, c)

    if not point_sets:
        return point_sets, seg_w, seg_h, 0, 0, 0, 0

    return (
        point_sets,
        seg_w,
        seg_h,
        int(min_row),
        int(max_row),
        int(min_col),
        int(max_col),
    )


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


def render_heatmap_svg(loaded_jsons: dict[str, Any]) -> str:
    """
    Build an SVG heatmap: each cell is colored by how many files selected it (0 = not drawn, max = darkest).
    Uses segment_size_px from the first file and a bounding box of all chosen points.
    """
    if not loaded_jsons:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    point_sets, seg_w, seg_h, min_r, max_r, min_c, max_c = _get_point_sets_and_geometry(loaded_jsons)
    if not point_sets:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    counts = _count_per_cell(point_sets)
    n_files = len(loaded_jsons)
    max_count = max(counts.values()) if counts else 1

    width = (max_c - min_c + 1) * seg_w
    height = (max_r - min_r + 1) * seg_h

    rects = []
    for (r, c), count in sorted(counts.items()):
        if count <= 0:
            continue
        t = count / max_count if max_count else 0
        fill = _rgb_interpolate(t)
        x = (c - min_c) * seg_w
        y = (r - min_r) * seg_h
        rects.append(f'<rect x="{x}" y="{y}" width="{seg_w}" height="{seg_h}" fill="{fill}" stroke="#333" stroke-width="0.5"/>')

    body = "\n".join(rects)
    return (
        '<?xml version="1.0"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<g>{body}</g></svg>'
    )


def render_intersection_svg(
    loaded_jsons: dict[str, Any],
    best_combination: tuple[str, ...] | None,
) -> str:
    """
    Build an SVG of the intersection: only cells selected in every file of best_combination
    (or in all files if best_combination is None). Same grid geometry as heatmap.
    """
    if not loaded_jsons:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    point_sets, seg_w, seg_h, min_r, max_r, min_c, max_c = _get_point_sets_and_geometry(loaded_jsons)
    if not point_sets:
        return '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'

    inter = _intersection_points(point_sets, best_combination)

    width = (max_c - min_c + 1) * seg_w
    height = (max_r - min_r + 1) * seg_h

    rects = []
    for r, c in sorted(inter):
        x = (c - min_c) * seg_w
        y = (r - min_r) * seg_h
        rects.append(f'<rect x="{x}" y="{y}" width="{seg_w}" height="{seg_h}" fill="steelblue" stroke="#1a5276" stroke-width="0.5"/>')

    body = "\n".join(rects)
    return (
        '<?xml version="1.0"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<g>{body}</g></svg>'
    )


def render_visualizations(
    loaded_jsons: dict[str, Any],
    best_combination: tuple[str, ...] | None,
) -> dict[str, str]:
    """
    Produce heatmap and intersection SVGs from feedback logs.
    best_combination is the tuple of file_ids from stability (used for intersection).
    Returns {"heatmap_svg": "...", "intersection_svg": "..."}.
    """
    return {
        "heatmap_svg": render_heatmap_svg(loaded_jsons),
        "intersection_svg": render_intersection_svg(loaded_jsons, best_combination),
    }
