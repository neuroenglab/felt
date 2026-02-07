import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel
from typing import Dict, Any
import os
import json
from datetime import datetime
from pathlib import Path
import argparse
from itertools import combinations

app = FastAPI()

LOGS_DIR = os.environ.get("LOGS_DIR", "logs")

#########################################################
################## Serve API Endpoints ##################
#########################################################

def check_file_setting_consistency(loaded_jsons):
    if not loaded_jsons:
        return
    first_file_data = list(loaded_jsons.values())[0]

    base_coarseness = first_file_data["feedbackLocation"]["coarsenessPercent"]
    base_image_path = first_file_data["feedbackLocation"]["image_path"]

    for file_id, log_data in loaded_jsons.items():
        if log_data["feedbackLocation"]["coarsenessPercent"] != base_coarseness:
            raise ValueError(f"File {file_id} has different coarseness than the first file")
        if log_data["feedbackLocation"]["image_path"] != base_image_path:
            raise ValueError(f"File {file_id} has different image path than the first file")

class ProcessFeedbackRequest(BaseModel):
    filenames: list[str]
    k: int

@app.post("/api/upload-logs")
async def upload_logs(files: list[UploadFile] = File(...)):
    """Upload feedback log JSON files. Returns paths for use with process-feedback."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    result = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".json"):
            continue
        content = await f.read()
        try:
            json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {f.filename}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in f.filename)
        out_name = f"uploaded_{timestamp}_{safe_name}"
        path = os.path.join(LOGS_DIR, out_name)
        with open(path, "wb") as fp:
            fp.write(content)
        result.append({"path": path, "filename": f.filename})
    return {"uploads": result}

@app.get("/api/logs")
async def list_logs():
    """List available feedback log files for process-feedback."""
    if not os.path.isdir(LOGS_DIR):
        return {"logs": []}
    logs = []
    for f in sorted(os.listdir(LOGS_DIR)):
        if f.endswith(".json"):
            path = os.path.join(LOGS_DIR, f)
            try:
                with open(path, "r") as fp:
                    data = json.load(fp)
                log_id = data.get("log_id", f)
            except (json.JSONDecodeError, KeyError):
                log_id = f
            logs.append({"path": path, "filename": f, "log_id": log_id})
    return {"logs": logs}

@app.post("/api/process-feedback")
async def process_feedback(data: ProcessFeedbackRequest):
    loaded_jsons = {}
    for file in data.filenames:
        # Assuming files are in the LOGS_DIR we set up earlier
        # file_path = os.path.join(LOGS_DIR, file)
        file_path = file
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                loaded_jsons[file] = json.load(f)

    # Check mathematical correctness
    num_files = len(loaded_jsons)
    if data.k > num_files:
        raise HTTPException(
            status_code=400,
            detail=f"Requested k={data.k} is larger than the {num_files} available files."
        )
    if data.k < 1:
        raise HTTPException(
            status_code=400,
            detail="k must be at least 1."
        )

    try:
        check_file_setting_consistency(loaded_jsons)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 1. Calculate the area of each individual file
    # And store the point sets for intersection
    areas = {}
    point_sets = {}
    segment_sizes = {} # To convert point counts back to area

    for file_id, log_data in loaded_jsons.items():
        fl = log_data["feedbackLocation"]
        w = fl["segment_size_px"]["w"]
        h = fl["segment_size_px"]["h"]

        # Create a set of (row, col) tuples
        rows = fl["chosenPoints"]["row"]
        cols = fl["chosenPoints"]["col"]
        points = set(zip(rows, cols))

        point_sets[file_id] = points
        areas[file_id] = len(points) * w * h
        segment_sizes[file_id] = (w, h)

    # 2. Find best_day_area (Max area from all individual files)
    if not areas:
        raise HTTPException(status_code=400, detail="No valid data found")

    max_area_file = max(areas, key=areas.get)
    best_day_area = areas[max_area_file]

    # 3. Calculate intersections for all k-sized combinations
    k = min(data.k, len(loaded_jsons))
    all_combinations = list(combinations(loaded_jsons.keys(), k))

    max_stable_overlap = 0.0
    best_combo = None

    for combo in all_combinations:
        # Start with the first file's points
        intersect_points = point_sets[combo[0]]
        # Intersect with all other files in the combination
        for other_file in combo[1:]:
            intersect_points = intersect_points.intersection(point_sets[other_file])

        # Calculate area of this intersection
        # Note: We assume coarseness is consistent across files being compared.
        # We use the segment size from the first file in the combo.
        w, h = segment_sizes[combo[0]]
        current_overlap_area = len(intersect_points) * w * h

        if current_overlap_area >= max_stable_overlap:
            max_stable_overlap = current_overlap_area
            best_combo = combo

    # 4. Calculate Stability
    stability_score = max_stable_overlap / best_day_area if best_day_area > 0 else 0

    return {
        "status": "success",
        "stability_score": stability_score,
        "stable_overlap_area": max_stable_overlap,
        "best_day_area": best_day_area,
        "max_area_file": max_area_file,
        "best_combination": best_combo,
    }

class FeedbackLog(BaseModel):
    log_id: str
    filename: str
    feedbackLocation: Dict[str, Any]

@app.post("/api/save-feedback")
async def save_feedback(log_data: FeedbackLog):
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = log_data.log_id + "_" + log_data.filename.replace(".svg", "_svg") + "_" + timestamp + ".json"
        file_path = os.path.join(LOGS_DIR, filename)

        payload = log_data.model_dump()
        payload["log_id"] = log_data.log_id
        payload["feedbackLocation"]["exported_at"] = timestamp

        with open(file_path, "w") as f:
            json.dump(payload, f, indent=2)

        return {"status": "success", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#########################################################
##################### Serve frontend ####################
#########################################################

frontend_path = Path(__file__).resolve().parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_path), html=True),
        name="frontend",
    )

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Serve frontend single-page app for non-api requests.
    """
    if full_path.startswith("api/"):
        return {"detail": "Not found"}
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"detail": "Frontend not built (npm run build)"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run perception feedback app")

    parser.add_argument(
        "--log-dir",
        type=str,
        default=LOGS_DIR,
        help="Directory where feedback logs will be stored",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind the server to",
    )

    args = parser.parse_args()

    os.environ["LOGS_DIR"] = args.log_dir
    LOGS_DIR = args.log_dir
    os.makedirs(LOGS_DIR, exist_ok=True)

    uvicorn.run("main:app", host=args.host, port=args.port, log_level="info", reload=True)
