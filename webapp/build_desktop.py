#!/usr/bin/env python3
"""
Build script for CTR FX Remeasurement Desktop Application

Run from the webapp/ directory:
    python build_desktop.py

Steps:
  1. Build Vue frontend  (npm run build in frontend-vue/)
  2. Run PyInstaller     (from backend/)
  3. Package into a zip  (CTR_FX_Remeasurement_vX.Y.Z.zip)

Output:
  backend/dist/CTR_FX_Remeasurement/CTR_FX_Remeasurement.exe
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

APP_NAME = "CTR_FX_Remeasurement"
APP_VERSION = "1.0.0"
WEBAPP_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = WEBAPP_DIR / "backend"
FRONTEND_VUE_DIR = WEBAPP_DIR / "frontend-vue"
FRONTEND_DIST_DIR = WEBAPP_DIR / "frontend-dist"
DIST_DIR = BACKEND_DIR / "dist" / APP_NAME
PACKAGE_NAME = f"{APP_NAME}_v{APP_VERSION}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def step(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")


def run(cmd, cwd=None, shell=False):
    """Run a command, raise on non-zero exit."""
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(str(c) for c in cmd)}")


# ---------------------------------------------------------------------------
# Step 1: Build Vue frontend
# ---------------------------------------------------------------------------

def build_frontend():
    step("Step 1 — Build Vue frontend")

    if not FRONTEND_VUE_DIR.exists():
        raise RuntimeError(f"frontend-vue/ not found at {FRONTEND_VUE_DIR}")

    # Clean old dist
    if FRONTEND_DIST_DIR.exists():
        shutil.rmtree(FRONTEND_DIST_DIR)
        ok("Removed old frontend-dist/")

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    run([npm, "install"], cwd=FRONTEND_VUE_DIR)
    ok("npm install done")

    run([npm, "run", "build"], cwd=FRONTEND_VUE_DIR)
    ok(f"Frontend built -> {FRONTEND_DIST_DIR}")


# ---------------------------------------------------------------------------
# Step 2: Build .exe with PyInstaller
# ---------------------------------------------------------------------------

def build_exe():
    step("Step 2 — Build .exe with PyInstaller")

    if not FRONTEND_DIST_DIR.exists():
        raise RuntimeError("frontend-dist/ not found — run Step 1 first")

    # Clean old PyInstaller outputs
    for artifact in ["build", "dist", f"{APP_NAME}.spec"]:
        path = BACKEND_DIR / artifact
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    ok("Cleaned old build/dist/spec")

    # --add-data uses os.pathsep as separator (';' on Windows, ':' on Unix)
    sep = os.pathsep

    # frontend-dist is one level up from backend/; destination inside _internal/
    frontend_src = str(FRONTEND_DIST_DIR)
    frontend_dst = "frontend-dist"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--console",                            # show console for debugging (change to --noconsole for release)
        f"--name={APP_NAME}",
        f"--add-data={frontend_src}{sep}{frontend_dst}",
        f"--add-data=services{sep}services",
        f"--add-data=models{sep}models",
        # Hidden imports — uvicorn internals that PyInstaller misses
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.loops.asyncio",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.http.h11_impl",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=uvicorn.lifespan.off",
        # multipart (file uploads)
        "--hidden-import=multipart",
        "--hidden-import=python_multipart",
        # pydantic v2
        "--hidden-import=pydantic",
        "--hidden-import=pydantic.deprecated.class_validators",
        "--hidden-import=pydantic_core",
        # pandas/numpy internals
        "--hidden-import=pandas._libs.tslibs.np_datetime",
        "--hidden-import=pandas._libs.tslibs.nattype",
        "--hidden-import=pandas._libs.tslibs.timedeltas",
        "--hidden-import=pandas._libs.tslibs.offsets",
        # openpyxl
        "--hidden-import=openpyxl",
        "--hidden-import=openpyxl.styles",
        "--hidden-import=openpyxl.styles.fills",
        # starlette
        "--hidden-import=starlette",
        "--hidden-import=starlette.routing",
        "--hidden-import=starlette.middleware",
        "--hidden-import=starlette.staticfiles",
        # collect-all for packages with dynamic imports
        "--collect-all=uvicorn",
        "--collect-all=fastapi",
        "--collect-all=starlette",
        "--collect-all=pydantic",
        "--collect-all=openpyxl",
        "--noconfirm",
        "--clean",
        "app.py",
    ]

    run(cmd, cwd=BACKEND_DIR)
    ok(f"Executable built -> {DIST_DIR / (APP_NAME + '.exe')}")


# ---------------------------------------------------------------------------
# Step 3: Package into zip
# ---------------------------------------------------------------------------

def package_zip():
    step("Step 3 — Create distributable zip")

    if not DIST_DIR.exists():
        raise RuntimeError(f"dist/{APP_NAME}/ not found — run Step 2 first")

    zip_path = WEBAPP_DIR / f"{PACKAGE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in DIST_DIR.rglob("*"):
            if file.is_file():
                arcname = Path(PACKAGE_NAME) / file.relative_to(DIST_DIR)
                zf.write(file, arcname)
        # Add README
        zf.writestr(
            f"{PACKAGE_NAME}/README.txt",
            README_TEXT,
        )

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    ok(f"Zip created -> {zip_path} ({size_mb:.1f} MB)")


README_TEXT = """\
CTR FX Remeasurement — Desktop Application
===========================================

Installation
------------
1. Extract this zip to any folder on your computer.
2. Open the CTR_FX_Remeasurement folder.
3. Double-click CTR_FX_Remeasurement.exe to launch.

The application will open in your default web browser automatically.

Data Storage
------------
Your configuration (account mapping, exchange rates, history) is saved to:
  %LOCALAPPDATA%\\CTR-FX-Remeasurement\\ctr_fx.db

This file persists across application updates — your data is never lost
when you install a new version of the .exe.

Processed output files are saved temporarily to:
  %LOCALAPPDATA%\\CTR-FX-Remeasurement\\uploads\\

Usage
-----
1. Go to Account Mapping and upload your account mapping file.
2. Go to Exchange Rates and upload your period-end rates file.
3. Go to Process CTR, upload your CTR file, and click Process CTR.
4. Download the output Excel file from the Results screen.

Troubleshooting
---------------
- If Windows Defender blocks the exe, click "More info" then "Run anyway".
- If the browser does not open, navigate to http://localhost:5001 manually.
- If you get a missing DLL error, install:
    Microsoft Visual C++ Redistributable (x64)
    https://aka.ms/vs/17/release/vc_redist.x64.exe

Requirements
------------
- Windows 10 or later (64-bit)
- No Python or other software required
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\n{'='*60}")
    print(f"  CTR FX Remeasurement — Desktop Build v{APP_VERSION}")
    print(f"{'='*60}")
    print(f"  webapp dir : {WEBAPP_DIR}")
    print(f"  backend dir: {BACKEND_DIR}")

    if not (WEBAPP_DIR / "backend" / "app.py").exists():
        fail("app.py not found. Run this script from the webapp/ directory.")
        return 1

    try:
        build_frontend()
        build_exe()
        package_zip()

        print(f"\n{'='*60}")
        print(f"  Build complete!")
        print(f"  Exe : {DIST_DIR / (APP_NAME + '.exe')}")
        print(f"  Zip : {WEBAPP_DIR / (PACKAGE_NAME + '.zip')}")
        print(f"{'='*60}\n")
        return 0

    except KeyboardInterrupt:
        fail("Build interrupted by user.")
        return 1
    except Exception as exc:
        fail(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
