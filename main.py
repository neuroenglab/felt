import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel
from typing import Dict, Any
import os
import json
from datetime import datetime
from pathlib import Path
import argparse

app = FastAPI()

LOGS_DIR = "logs"

#########################################################
################## Serve API Endpoints ##################
#########################################################

class FeedbackLog(BaseModel):
    log_id: str
    filename: str
    feedbackLocation: Dict[str, Any]

@app.post("/api/save-feedback")
async def save_feedback(log_data: FeedbackLog):
    try:
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = log_data.log_id + "_" + log_data.filename.replace(".svg", "_svg") + "_" + timestamp + ".json"
        os.makedirs(LOGS_DIR, exist_ok=True)
        file_path = os.path.join(LOGS_DIR, filename)

        log_data.model_dump()["log_id"] = log_data.log_id
        log_data.model_dump()["feedbackLocation"]["exported_at"] = timestamp

        # Write the data to disk
        with open(file_path, "w") as f:
            json.dump(log_data.model_dump(), f, indent=2)

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

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Run perception feedback app")
    parser.add_argument(
        "--log-dir",
        type=str,
        default=LOGS_DIR,
        help="Directory where feedback logs will be stored",
    )
    args = parser.parse_args()

    LOGS_DIR = args.log_dir

    uvicorn.run("main:app", port=5000, log_level="debug", reload=True)
