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

from src.stability import compute_stability
from src.visualization import render_visualizations

app = FastAPI()

LOGS_DIR = os.environ.get("LOGS_DIR", "logs")
IMAGES_DIR = os.environ.get(
    "IMAGES_DIR", str(Path(__file__).resolve().parent / "uploads")
)

os.makedirs(IMAGES_DIR, exist_ok=True)
# Ensure visualization module sees the same uploads directory
os.environ["IMAGES_DIR"] = IMAGES_DIR

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
    include_original: bool = True

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


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Upload a body-part SVG image for reuse and visualization overlays."""
    if not file.filename or not file.filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Only SVG files are supported.")

    os.makedirs(IMAGES_DIR, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file.filename)
    out_path = os.path.join(IMAGES_DIR, safe_name)

    contents = await file.read()
    try:
        with open(out_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to store image: {e}") from e

    return {"filename": safe_name, "url": f"/uploads/{safe_name}"}


@app.get("/api/images")
async def list_images():
    """List available uploaded body-part SVG images."""
    if not os.path.isdir(IMAGES_DIR):
        return {"images": []}

    images = []
    for f in sorted(os.listdir(IMAGES_DIR)):
        if f.lower().endswith(".svg"):
            images.append({"filename": f, "url": f"/uploads/{f}"})
    return {"images": images}

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


class DeleteLogsRequest(BaseModel):
    paths: list[str]


def _path_under(base_dir: str, path: str) -> bool:
    """Return True if path is under base_dir (no path traversal)."""
    base = os.path.realpath(base_dir)
    resolved = os.path.realpath(path)
    return resolved == base or resolved.startswith(base + os.sep)


@app.post("/api/logs/delete")
async def delete_logs(body: DeleteLogsRequest):
    """Delete selected log files by path. Paths must be under LOGS_DIR."""
    deleted = []
    for path in body.paths:
        if not _path_under(LOGS_DIR, path):
            raise HTTPException(status_code=400, detail=f"Invalid path: {path}")
        if os.path.isfile(path):
            try:
                os.remove(path)
                deleted.append(path)
            except OSError as e:
                raise HTTPException(status_code=500, detail=str(e)) from e
    return {"deleted": deleted}


@app.delete("/api/images/{filename}")
async def delete_image(filename: str):
    """Delete an uploaded body-part image by filename."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    if safe != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join(IMAGES_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        os.remove(path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "deleted", "filename": safe}

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

    try:
        result = compute_stability(loaded_jsons, data.k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    visuals = render_visualizations(
        loaded_jsons,
        result.get("best_combination"),
        include_original=data.include_original,
    )

    heatmap_metadata = {
        "source": "all_selected_logs",
        "num_files": num_files,
    }
    intersection_metadata = {
        "source": "best_k_combination",
        "k": data.k,
        "file_ids": list(result.get("best_combination") or []),
    }

    response: Dict[str, Any] = {
        "status": "success",
        **result,
        **visuals,
        "heatmap_metadata": heatmap_metadata,
        "intersection_metadata": intersection_metadata,
    }
    return response

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

base_dir = Path(__file__).resolve().parent
frontend_path = base_dir / "frontend" / "dist"
images_path = Path(IMAGES_DIR)

app.mount(
    "/uploads",
    StaticFiles(directory=str(images_path)),
    name="uploads",
)

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Serve frontend single-page app: real files when they exist, else index.html
    so client-side routes (e.g. /process) work on reload.
    """
    if full_path.startswith("api/"):
        return {"detail": "Not found"}
    if not frontend_path.exists():
        return {"detail": "Frontend not built (npm run build)"}
    # Serve existing static files (e.g. vite.svg, assets/*)
    safe_path = (frontend_path / full_path).resolve()
    if full_path and safe_path.is_file() and str(safe_path).startswith(str(frontend_path)):
        return FileResponse(safe_path)
    # Otherwise serve index.html for SPA client-side routing
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
