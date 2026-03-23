#!/usr/bin/env python3
"""
CTR FX Remeasurement Application

A web application for processing consolidated transaction reports
and calculating FX gain/loss per GL account.

Can run as:
- Web server: python app.py
- Desktop app: python app.py --desktop
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import uuid
import time
import threading
import webbrowser
import argparse
from datetime import datetime
from typing import Dict
from pathlib import Path
import uvicorn

from models.schemas import JobStatus
from services.config_store import (
    load_account_mapping, save_account_mapping, reset_account_mapping,
    parse_account_mapping_file, merge_account_mapping, export_account_mapping,
    load_exchange_rates, save_exchange_rates, reset_exchange_rates,
    parse_exchange_rates_file, merge_exchange_rates, export_exchange_rates,
    save_history_entry, list_history, get_history_entry, rollback_to_entry,
)

# Global mode flag
DESKTOP_MODE = False

app = FastAPI(title="CTR FX Remeasurement", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage
jobs: Dict[str, JobStatus] = {}


def get_upload_dir():
    """Get the upload directory path, handling PyInstaller executable.

    Desktop mode: %LOCALAPPDATA%/CTR-FX-Remeasurement/uploads/
    Dev mode: backend/uploads/
    """
    if getattr(sys, 'frozen', False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_path = Path(local_app_data) / "CTR-FX-Remeasurement"
        else:
            base_path = Path.home() / ".local" / "share" / "CTR-FX-Remeasurement"
        base_path.mkdir(parents=True, exist_ok=True)
    else:
        base_path = Path(__file__).parent

    upload_dir = base_path / "uploads"
    upload_dir.mkdir(exist_ok=True)
    return upload_dir

UPLOAD_DIR = get_upload_dir()


def cleanup_old_files():
    """Clean up files older than 1 hour"""
    try:
        current_time = time.time()
        for file_path in UPLOAD_DIR.glob("*"):
            if current_time - file_path.stat().st_mtime > 3600:
                try:
                    file_path.unlink()
                except OSError as e:
                    if e.errno != 32:
                        print(f"Could not delete {file_path}: {e}")
    except Exception as e:
        print(f"Cleanup error: {e}")


# ---------------------------------------------------------------------------
# Config endpoints — Account Mapping
# ---------------------------------------------------------------------------

@app.get("/config/account-mapping")
async def get_account_mapping():
    """Return the current saved account mapping."""
    mapping = load_account_mapping()
    return {
        "success": True,
        "count": len(mapping),
        "mapping": mapping,
    }


@app.post("/config/account-mapping")
async def upload_account_mapping(
    file: UploadFile = File(...),
    mode: str = Form("replace"),
):
    """
    Upload an account mapping file (CSV or Excel).

    Modes:
      - "replace" — clear existing config, load from file
      - "merge"   — add new entries, update existing entries with same Account Number
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, and .csv files are accepted.")

    if mode not in ("replace", "merge"):
        raise HTTPException(status_code=400, detail="Mode must be 'replace' or 'merge'.")

    temp_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        incoming, warnings = parse_account_mapping_file(str(temp_path))

        if not incoming:
            raise HTTPException(status_code=400, detail=f"No valid entries found. {'; '.join(warnings)}")

        if mode == "merge":
            existing = load_account_mapping()
            final = merge_account_mapping(existing, incoming)
        else:
            final = incoming

        save_account_mapping(final)

        save_history_entry(
            action="upload",
            config_type="account_mapping",
            mode=mode,
            source_filename=file.filename,
            details={"entries_in_file": len(incoming), "total_after": len(final), "warnings": warnings},
        )

        return {
            "success": True,
            "mode": mode,
            "count": len(final),
            "new_entries": len(incoming),
            "warnings": warnings,
            "mapping": final,
        }
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.get("/config/account-mapping/download")
async def download_account_mapping():
    """Download the current account mapping as an Excel file for sharing."""
    mapping = load_account_mapping()
    if not mapping:
        raise HTTPException(status_code=404, detail="No account mapping configured yet.")

    output_path = UPLOAD_DIR / f"account_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_account_mapping(str(output_path))

    return FileResponse(
        path=str(output_path),
        filename="account_mapping.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.delete("/config/account-mapping")
async def delete_account_mapping():
    """Reset (clear) the saved account mapping."""
    save_history_entry(action="reset", config_type="account_mapping")
    reset_account_mapping()
    return {"success": True, "message": "Account mapping cleared."}


# ---------------------------------------------------------------------------
# Config endpoints — Exchange Rates
# ---------------------------------------------------------------------------

@app.get("/config/exchange-rates")
async def get_exchange_rates():
    """Return the current saved exchange rates."""
    rates = load_exchange_rates()
    return {
        "success": True,
        "count": len(rates),
        "rates": rates,
    }


@app.post("/config/exchange-rates")
async def upload_exchange_rates(
    file: UploadFile = File(...),
    mode: str = Form("replace"),
):
    """
    Upload an exchange rates file (CSV or Excel).

    Modes:
      - "replace" — clear existing config, load from file
      - "merge"   — add new currencies, update existing currencies with new rate
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, and .csv files are accepted.")

    if mode not in ("replace", "merge"):
        raise HTTPException(status_code=400, detail="Mode must be 'replace' or 'merge'.")

    temp_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        incoming, warnings = parse_exchange_rates_file(str(temp_path))

        if not incoming:
            raise HTTPException(status_code=400, detail=f"No valid entries found. {'; '.join(warnings)}")

        if mode == "merge":
            existing = load_exchange_rates()
            final = merge_exchange_rates(existing, incoming)
        else:
            final = incoming

        save_exchange_rates(final)

        save_history_entry(
            action="upload",
            config_type="exchange_rates",
            mode=mode,
            source_filename=file.filename,
            details={"entries_in_file": len(incoming), "total_after": len(final), "warnings": warnings},
        )

        return {
            "success": True,
            "mode": mode,
            "count": len(final),
            "new_entries": len(incoming),
            "warnings": warnings,
            "rates": final,
        }
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.get("/config/exchange-rates/download")
async def download_exchange_rates():
    """Download the current exchange rates as an Excel file for sharing."""
    rates = load_exchange_rates()
    if not rates:
        raise HTTPException(status_code=404, detail="No exchange rates configured yet.")

    output_path = UPLOAD_DIR / f"exchange_rates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_exchange_rates(str(output_path))

    return FileResponse(
        path=str(output_path),
        filename="exchange_rates.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.delete("/config/exchange-rates")
async def delete_exchange_rates():
    """Reset (clear) the saved exchange rates."""
    save_history_entry(action="reset", config_type="exchange_rates")
    reset_exchange_rates()
    return {"success": True, "message": "Exchange rates cleared."}


# ---------------------------------------------------------------------------
# History & Rollback endpoints
# ---------------------------------------------------------------------------

@app.get("/history")
async def get_history(limit: int = 50):
    """List config change history, most recent first."""
    entries = list_history(limit=limit)
    return {
        "success": True,
        "count": len(entries),
        "entries": entries,
    }


@app.get("/history/{entry_id}")
async def get_history_detail(entry_id: str):
    """Get full history entry including config snapshots."""
    entry = get_history_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found.")
    return {"success": True, "entry": entry}


@app.post("/history/{entry_id}/rollback")
async def rollback_config(entry_id: str, config_type: str = "both"):
    """
    Rollback configs to a previous history entry's snapshot.

    Args:
        entry_id: History entry ID to rollback to.
        config_type: "account_mapping", "exchange_rates", or "both" (default).
    """
    if config_type not in ("account_mapping", "exchange_rates", "both"):
        raise HTTPException(
            status_code=400,
            detail="config_type must be 'account_mapping', 'exchange_rates', or 'both'.",
        )

    result = rollback_to_entry(entry_id, config_type=config_type)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return result


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the main page"""
    frontend_file = get_frontend_path() / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return {"message": "CTR FX Remeasurement API", "docs": "/docs"}


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get processing status for a job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in jobs.values() if j.status in ["pending", "processing"]]),
        "mode": "desktop" if DESKTOP_MODE else "web"
    }


@app.delete("/cleanup")
async def cleanup_files():
    """Manual cleanup endpoint"""
    try:
        cleanup_old_files()
        current_time = datetime.now()
        to_remove = []
        for job_id, job in jobs.items():
            if job.completed_at and (current_time - job.completed_at).seconds > 3600:
                to_remove.append(job_id)

        for job_id in to_remove:
            del jobs[job_id]

        return {"message": f"Cleanup completed. Removed {len(to_remove)} old jobs."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# ---------------------------------------------------------------------------
# Static files & dual-mode server
# ---------------------------------------------------------------------------

def get_frontend_path():
    """Get the frontend directory path, handling PyInstaller executable"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent / "_internal"
    else:
        base_path = Path(__file__).parent.parent

    return base_path / "frontend-dist"


frontend_path = get_frontend_path()
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


def open_browser(url: str):
    print(f"Opening browser to: {url}")
    webbrowser.open(url)


def run_desktop_mode():
    global DESKTOP_MODE
    DESKTOP_MODE = True

    host = "localhost"
    port = 5001

    print("=" * 60)
    print("CTR FX Remeasurement Desktop Application")
    print("=" * 60)
    print(f"Starting application on http://{host}:{port}")
    print("The application will open in your default browser...")
    print("Close this window to stop the application.")
    print("=" * 60)

    cleanup_thread = threading.Thread(target=lambda: threading.Timer(3600, cleanup_old_files).start())
    cleanup_thread.daemon = True
    cleanup_thread.start()

    browser_thread = threading.Timer(1.5, lambda: open_browser(f"http://{host}:{port}"))
    browser_thread.start()

    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


def run_web_mode():
    global DESKTOP_MODE
    DESKTOP_MODE = False

    host = "0.0.0.0"
    port = 8000

    print("=" * 60)
    print("CTR FX Remeasurement Web Application")
    print("=" * 60)
    print(f"Starting server on http://{host}:{port}")
    print("Access the application via web browser")
    print("API documentation: http://localhost:8000/docs")
    print("=" * 60)

    if "--reload" in sys.argv:
        uvicorn.run("app:app", host=host, port=port, reload=True)
    else:
        uvicorn.run(app, host=host, port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="CTR FX Remeasurement Application")
    parser.add_argument("--desktop", action="store_true", help="Run in desktop mode")
    args = parser.parse_args()

    is_executable = getattr(sys, 'frozen', False)

    try:
        if args.desktop or is_executable:
            run_desktop_mode()
        else:
            run_web_mode()
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
    except Exception as e:
        print(f"Error starting application: {e}")
    finally:
        print("Cleaning up...")
        cleanup_old_files()


if __name__ == "__main__":
    main()
