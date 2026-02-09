from itertools import combinations


def compute_stability(loaded_jsons: dict, k: int) -> dict:
    """
    Compute stability score from feedback log data.
    loaded_jsons: dict mapping file_id -> log data (with feedbackLocation, chosenPoints, etc.)
    k: number of files to intersect for stability.
    Returns dict with stability_score, stable_overlap_area, best_day_area, max_area_file, best_combination.
    Raises ValueError if no valid data.
    """
    # 1. Calculate the area of each individual file and store point sets for intersection
    areas = {}
    point_sets = {}
    segment_sizes = {}

    for file_id, log_data in loaded_jsons.items():
        fl = log_data["feedbackLocation"]
        w = fl["segment_size_px"]["w"]
        h = fl["segment_size_px"]["h"]

        rows = fl["chosenPoints"]["row"]
        cols = fl["chosenPoints"]["col"]
        points = set(zip(rows, cols))

        point_sets[file_id] = points
        areas[file_id] = len(points) * w * h
        segment_sizes[file_id] = (w, h)

    # 2. Find best_day_area (max area from all individual files)
    if not areas:
        raise ValueError("No valid data found")

    max_area_file = max(areas, key=areas.get)
    best_day_area = areas[max_area_file]

    # 3. Calculate intersections for all k-sized combinations
    k = min(k, len(loaded_jsons))
    all_combinations = list(combinations(loaded_jsons.keys(), k))

    max_stable_overlap = 0.0
    best_combo = None

    for combo in all_combinations:
        intersect_points = point_sets[combo[0]]
        for other_file in combo[1:]:
            intersect_points = intersect_points.intersection(point_sets[other_file])

        w, h = segment_sizes[combo[0]]
        current_overlap_area = len(intersect_points) * w * h

        if current_overlap_area >= max_stable_overlap:
            max_stable_overlap = current_overlap_area
            best_combo = combo

    # 4. Calculate stability score
    stability_score = max_stable_overlap / best_day_area if best_day_area > 0 else 0

    return {
        "stability_score": stability_score,
        "stable_overlap_area": max_stable_overlap,
        "best_day_area": best_day_area,
        "max_area_file": max_area_file,
        "best_combination": best_combo,
    }
