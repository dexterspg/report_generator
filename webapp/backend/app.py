#!/usr/bin/env python3
"""
CTR FX Remeasurement Application

Slice 1: App shell — FastAPI skeleton with dual-mode server.
No domain logic, no config endpoints, no processing yet.

Can run as:
- Web server:    python app.py
- Desktop app:   python app.py --desktop
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import threading
import webbrowser
import argparse
from datetime import datetime
from pathlib import Path
import uvicorn

from services.config_store import (
    get_account_mapping,
    get_account_mapping_count,
    parse_account_mapping_file,
    save_account_mapping_replace,
    save_account_mapping_merge,
    reset_account_mapping,
    export_account_mapping,
)


# ---------------------------------------------------------------------------
# Global mode flag — set once at startup, never changes after
# ---------------------------------------------------------------------------
DESKTOP_MODE = False

# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------
app = FastAPI(title="CTR FX Remeasurement", version="1.0.0")

# CORS middleware — allows the Vue dev server (port 3000) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Core endpoints — Slice 1 only needs health and root
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the frontend or show API info"""
    frontend_file = get_frontend_path() / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return {"message": "CTR FX Remeasurement API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Health check — also exposes the execution mode (desktop vs web)"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mode": "desktop" if DESKTOP_MODE else "web",
    }


# ---------------------------------------------------------------------------
# Configuration — Account Mapping (Slice 2)
# ---------------------------------------------------------------------------

@app.get("/config/account-mapping")
async def get_account_mapping_endpoint():
    """Return the current saved account mapping and row count."""
    mapping = get_account_mapping()
    return {"mapping": mapping, "count": len(mapping)}


@app.post("/config/account-mapping")
async def upload_account_mapping(
    file: UploadFile = File(...),
    mode: str = Form("replace"),
):
    """
    Upload an account mapping file (CSV/Excel).

    Form fields:
      file  — multipart file upload (.xlsx, .xls, .csv)
      mode  — "replace" (default) or "merge"
    """
    allowed = {".xlsx", ".xls", ".csv"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: .xlsx, .xls, .csv",
        )

    mode = mode.strip().lower()
    if mode not in ("replace", "merge"):
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Use 'replace' or 'merge'.",
        )

    try:
        records = parse_account_mapping_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if mode == "replace":
        count = save_account_mapping_replace(records)
    else:
        count = save_account_mapping_merge(records)

    return {
        "status": "ok",
        "mode": mode,
        "rows_processed": count,
        "total_count": get_account_mapping_count(),
    }


@app.get("/config/account-mapping/download")
async def download_account_mapping():
    """Export the current account mapping as a styled .xlsx file."""
    data = export_account_mapping()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"account_mapping_{timestamp}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/config/account-mapping")
async def clear_account_mapping():
    """Clear all saved account mapping data."""
    reset_account_mapping()
    return {"status": "ok", "count": 0}


# ---------------------------------------------------------------------------
# Static files — serve the built Vue frontend
# ---------------------------------------------------------------------------

def get_frontend_path():
    """
    Resolve the frontend directory.

    PyInstaller bundles frontend-dist/ inside _internal/ next to the .exe.
    In dev, it's one level up from backend/.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent / "_internal"
    else:
        base_path = Path(__file__).parent.parent

    return base_path / "frontend-dist"


frontend_path = get_frontend_path()
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


# ---------------------------------------------------------------------------
# Dual-mode server launcher
# ---------------------------------------------------------------------------

def open_browser(url: str):
    print(f"Opening browser to: {url}")
    webbrowser.open(url)


def run_desktop_mode():
    """Desktop mode: localhost:5001, auto-opens browser, single user"""
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

    # Open browser after a short delay so the server is ready
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
    """Web mode: 0.0.0.0:8000, multi-user server"""
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

    is_executable = getattr(sys, "frozen", False)

    try:
        if args.desktop or is_executable:
            run_desktop_mode()
        else:
            run_web_mode()
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
    except Exception as e:
        print(f"Error starting application: {e}")


if __name__ == "__main__":
    main()
