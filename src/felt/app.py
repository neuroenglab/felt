"""The FastAPI application of FELT: the API of the marking page, and the page itself.

``create_app(settings)`` builds one application for one set of settings. The
service state (the console link and the marking-client leases) hangs on
``app.state``, so a Python caller that started the server can read it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from felt.clients import MarkingClients
from felt.console import ConsoleLink
from felt.settings import Settings
from felt.stability import compute_stability
from felt.visualization import render_visualizations

NOT_BUILT = {"detail": "Frontend not built: the package ships without its marking page"}


# --- request and log models ---------------------------------------------------------


class ProcessFeedbackRequest(BaseModel):
    filenames: list[str]
    k: int
    include_original: bool = True


class DeleteLogsRequest(BaseModel):
    paths: list[str]


class TrialRef(BaseModel):
    """The trial a painting scores (data dictionary section 4.6)."""
    subject_code: str
    sequence_id: str
    trial_id: str


class FeedbackLog(BaseModel):
    log_id: str
    filename: str
    feedbackLocation: Dict[str, Any]
    # Present only when FELT is linked to a console.
    trial: TrialRef | None = None
    felt: bool | None = None
    # What the subject reports beside the painting of a sensation. A target
    # carries neither.
    pain: bool | None = None
    intensity: float | None = Field(default=None, ge=0, le=10)


# --- helpers ------------------------------------------------------------------------


def _safe_name(text: str) -> str:
    """A file name part without a separator."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in text)


def _path_under(base_dir: Path, path: str) -> bool:
    """True if path is under base_dir (no path traversal)."""
    base = os.path.realpath(base_dir)
    resolved = os.path.realpath(path)
    return resolved == base or resolved.startswith(base + os.sep)


def check_file_setting_consistency(loaded_jsons: dict[str, Any]) -> None:
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


# --- the application ----------------------------------------------------------------


def create_app(settings: Settings | None = None) -> FastAPI:
    """The FELT application for ``settings`` (the defaults when None).

    The log and image folders are created. The marking page is served when the
    package carries it under ``settings.static_dir``.
    """
    settings = settings or Settings()
    log_dir = settings.log_dir
    images_dir = settings.images_dir
    root_path = settings.root_path
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(settings.hands_dir, exist_ok=True)

    app = FastAPI(root_path=root_path, title="FELT")
    app.state.settings = settings
    app.state.console = ConsoleLink(settings.console_url)
    app.state.clients = MarkingClients()

    def console() -> ConsoleLink:
        return app.state.console

    def clients() -> MarkingClients:
        return app.state.clients

    # --- logs and images ---

    @app.post("/api/upload-logs")
    async def upload_logs(files: list[UploadFile] = File(...)):
        """Upload feedback log JSON files. Returns paths for use with process-feedback."""
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
            out_name = f"uploaded_{timestamp}_{_safe_name(f.filename)}"
            path = os.path.join(log_dir, out_name)
            with open(path, "wb") as fp:
                fp.write(content)
            result.append({"path": path, "filename": f.filename})
        return {"uploads": result}

    @app.post("/api/upload-image")
    async def upload_image(file: UploadFile = File(...)):
        """Upload a body-part SVG image for reuse and visualization overlays."""
        if not file.filename or not file.filename.lower().endswith(".svg"):
            raise HTTPException(status_code=400, detail="Only SVG files are supported.")
        safe_name = _safe_name(file.filename)
        out_path = os.path.join(images_dir, safe_name)
        contents = await file.read()
        try:
            with open(out_path, "wb") as f:
                f.write(contents)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to store image: {e}") from e
        return {"filename": safe_name, "url": f"{root_path}/uploads/{safe_name}"}

    @app.get("/api/images")
    async def list_images():
        """List available uploaded body-part SVG images."""
        if not os.path.isdir(images_dir):
            return {"images": []}
        images = [
            {"filename": f, "url": f"{root_path}/uploads/{f}"}
            for f in sorted(os.listdir(images_dir))
            if f.lower().endswith(".svg")
        ]
        return {"images": images}

    @app.get("/api/logs")
    async def list_logs():
        """List available feedback log files for process-feedback."""
        if not os.path.isdir(log_dir):
            return {"logs": []}
        logs = []
        for f in sorted(os.listdir(log_dir)):
            if not f.endswith(".json"):
                continue
            path = os.path.join(log_dir, f)
            try:
                with open(path, "r") as fp:
                    data = json.load(fp)
                log_id = data.get("log_id", f)
            except (json.JSONDecodeError, KeyError, OSError):
                log_id = f
            logs.append({"path": path, "filename": f, "log_id": log_id})
        return {"logs": logs}

    @app.post("/api/logs/delete")
    async def delete_logs(body: DeleteLogsRequest):
        """Delete selected log files by path. Paths must be under the log folder."""
        deleted = []
        for path in body.paths:
            if not _path_under(log_dir, path):
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
        if ".." in filename or "/" in filename or "\\" in filename or _safe_name(filename) != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        path = os.path.join(images_dir, filename)
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="Image not found")
        try:
            os.remove(path)
        except OSError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {"status": "deleted", "filename": filename}

    @app.post("/api/process-feedback")
    async def process_feedback(data: ProcessFeedbackRequest):
        loaded_jsons = {}
        for file_path in data.filenames:
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    loaded_jsons[file_path] = json.load(f)

        num_files = len(loaded_jsons)
        if data.k > num_files:
            raise HTTPException(
                status_code=400,
                detail=f"Requested k={data.k} is larger than the {num_files} available files.",
            )
        if data.k < 1:
            raise HTTPException(status_code=400, detail="k must be at least 1.")
        try:
            check_file_setting_consistency(loaded_jsons)
            result = compute_stability(loaded_jsons, data.k)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        visuals = render_visualizations(
            loaded_jsons,
            result.get("best_combination"),
            include_original=data.include_original,
            images_dir=images_dir,
        )
        response: Dict[str, Any] = {
            "status": "success",
            **result,
            **visuals,
            "heatmap_metadata": {"source": "all_selected_logs", "num_files": num_files},
            "intersection_metadata": {
                "source": "best_k_combination",
                "k": data.k,
                "file_ids": list(result.get("best_combination") or []),
            },
        }
        return response

    # --- the console link and the marking clients ---

    @app.get("/api/trial")
    def read_trial(wait: float = Query(default=0, ge=0, le=25)):
        """When idle, wait for the next console sequence instead of polling it."""
        return console().trial(wait=wait)

    @app.get("/api/clients")
    def marking_clients():
        return clients().status()

    @app.put("/api/clients/{client_id}", status_code=204)
    def marking_heartbeat(client_id: str):
        clients().touch(client_id)

    @app.delete("/api/clients/{client_id}", status_code=204)
    def marking_disconnected(client_id: str):
        clients().remove(client_id)

    # A plain def, so FastAPI runs the console request in a worker thread and the
    # event loop keeps serving the other tablets.
    @app.post("/api/save-feedback")
    def save_feedback(log_data: FeedbackLog):
        try:
            os.makedirs(log_dir, exist_ok=True)
            now = datetime.now()
            if log_data.trial is not None:
                # A send names the trial. Two sends inside one second must not
                # overwrite each other, so the name carries microseconds, and the
                # export time is the ISO time the request carries.
                timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
                exported_at = now.astimezone().isoformat()
                stem = _safe_name(f"{log_data.trial.subject_code}_{log_data.trial.trial_id}")
            else:
                # The unlinked page and the manual mode export as they always did.
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                exported_at = timestamp
                stem = log_data.log_id
            filename = stem + "_" + log_data.filename.replace(".svg", "_svg") + "_" + timestamp + ".json"
            file_path = os.path.join(log_dir, filename)

            payload = log_data.model_dump()
            payload["log_id"] = log_data.log_id
            payload["feedbackLocation"]["exported_at"] = exported_at
            # A FELT without the console link writes the file it always wrote.
            for field in ("trial", "felt", "pain", "intensity"):
                if payload.get(field) is None:
                    payload.pop(field, None)

            with open(file_path, "w") as f:
                json.dump(payload, f, indent=2)

            response: Dict[str, Any] = {"status": "success", "filename": filename}
            link = console()
            if link.linked and log_data.trial is not None:
                response["console"] = link.send_felt(payload)
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # --- the page ---

    app.mount("/uploads", StaticFiles(directory=str(images_dir)), name="uploads")
    # The hand images of the linked page ship with the package, so the tablet
    # finds them without an upload.
    app.mount("/hands", StaticFiles(directory=str(settings.hands_dir)), name="hands")

    static_dir = settings.static_dir.resolve()

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """The marking page: real files when they exist, else index.html, so
        client-side routes (for example /process) work on reload."""
        if full_path.startswith("api/"):
            return {"detail": "Not found"}
        if not settings.frontend_built:
            return NOT_BUILT
        safe_path = (static_dir / full_path).resolve()
        if full_path and safe_path.is_file() and str(safe_path).startswith(str(static_dir)):
            return FileResponse(safe_path)
        # The page itself is never cached, so a tablet picks up a new release on
        # its next load. The bundles it names carry a hash and cache freely.
        return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-cache"})

    return app


def factory() -> FastAPI:
    """The application from the environment, for ``uvicorn --factory felt.app:factory``."""
    return create_app(Settings.from_env())
