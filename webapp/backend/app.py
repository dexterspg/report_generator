#!/usr/bin/env python3
"""
CTR Mapper Application

A web application for processing consolidated transaction reports
and generating formatted poliza ledger Excel files.

Can run as:
- Web server: python app.py
- Desktop app: python app.py --desktop
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
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
from typing import Dict, Any
import asyncio
from pathlib import Path
import uvicorn

from services.excel_processor import ExcelProcessor
from services.maturity_analysis_processor import MaturityAnalysisProcessor
from models.schemas import ProcessingRequest, ProcessingResponse, JobStatus, MaturityAnalysisRequest

# Global mode flag
DESKTOP_MODE = False

app = FastAPI(title="CTR Mapper", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors and job storage
processor = ExcelProcessor()
maturity_processor = MaturityAnalysisProcessor()
jobs: Dict[str, JobStatus] = {}

# Ensure upload directory exists
def get_upload_dir():
    """Get the upload directory path, handling PyInstaller executable"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        base_path = Path(sys.executable).parent
    else:
        # Running as script
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
            if current_time - file_path.stat().st_mtime > 3600:  # 1 hour
                try:
                    file_path.unlink()
                except OSError as e:
                    # Skip files that are in use
                    if e.errno != 32:  # Not "file in use" error
                        print(f"Could not delete {file_path}: {e}")
    except Exception as e:
        print(f"Cleanup error: {e}")


async def process_file_background(job_id: str, input_path: str, output_path: str, 
                                request_params: ProcessingRequest, company_code: str = None):
    """Background task for file processing"""
    try:
        jobs[job_id].status = "processing"
        
        start_time = time.perf_counter()
        result = processor.process_file(
            source_file_path=input_path,
            output_file_path=output_path,
            input_header_start=request_params.input_header_start,
            input_data_start=request_params.input_data_start,
            template_header_start=request_params.template_header_start,
            template_data_start=request_params.template_data_start,
            company_code=company_code
        )
        end_time = time.perf_counter()
        
        jobs[job_id].completed_at = datetime.now()
        jobs[job_id].result = result
        jobs[job_id].result["processing_time"] = end_time - start_time
        
        if result["success"]:
            jobs[job_id].status = "completed"
        else:
            jobs[job_id].status = "failed"
            jobs[job_id].error = result.get("error")
            
    except Exception as e:
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(e)
        jobs[job_id].completed_at = datetime.now()
        print(f"Processing error for job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()


@app.get("/")
async def root():
    """Serve the main page"""
    frontend_file = get_frontend_path() / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return {"message": "Excel Consolidation Report Mapper API", "docs": "/docs"}


@app.post("/upload", response_model=ProcessingResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    input_header_start: int = Form(27),
    input_data_start: int = Form(28),
    template_header_start: int = Form(1),
    template_data_start: int = Form(2),
    company_code: str = Form(None)
):
    """Upload and process Excel file"""
    
    # Debug logging
    print(f"Received upload request - company_code: {company_code}")
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Clean up old files
    cleanup_old_files()
    
    try:
        # Save uploaded file
        input_path = UPLOAD_DIR / f"{job_id}_input_{file.filename}"
        output_path = UPLOAD_DIR / f"{job_id}_output_poliza_ledger.xlsx"
        
        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create job status
        jobs[job_id] = JobStatus(
            job_id=job_id,
            status="pending",
            created_at=datetime.now()
        )
        
        # Create processing request
        request_params = ProcessingRequest(
            input_header_start=input_header_start,
            input_data_start=input_data_start,
            template_header_start=template_header_start,
            template_data_start=template_data_start
        )
        
        # Start background processing
        background_tasks.add_task(
            process_file_background,
            job_id,
            str(input_path),
            str(output_path),
            request_params,
            company_code
        )
        
        return ProcessingResponse(
            success=True,
            message="File uploaded successfully. Processing started.",
            job_id=job_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get processing status for a job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download processed file"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    output_path = UPLOAD_DIR / f"{job_id}_output_poliza_ledger.xlsx"
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        path=str(output_path),
        filename=f"poliza_ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.post("/extract-company-codes")
async def extract_company_codes(
    file: UploadFile = File(...),
    input_header_start: int = Form(27)
):
    """Extract unique Company Code values from uploaded Excel file"""
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    try:
        # Save uploaded file temporarily
        temp_id = str(uuid.uuid4())
        temp_path = UPLOAD_DIR / f"{temp_id}_temp_{file.filename}"
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Read the Excel file to extract Company Code values
        import pandas as pd
        df = pd.read_excel(temp_path, header=input_header_start - 1)
        
        # Check if Company Code column exists
        if 'Company Code' not in df.columns:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(status_code=400, detail="Company Code column not found in the uploaded file")
        
        # Extract unique Company Code values
        unique_company_codes = df['Company Code'].dropna().unique().tolist()
        
        # Sort the values for better UX
        unique_company_codes = sorted([str(code) for code in unique_company_codes])
        
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
        
        return {
            "success": True,
            "company_codes": unique_company_codes,
            "total_count": len(unique_company_codes)
        }
        
    except Exception as e:
        # Clean up temp file in case of error
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to extract company codes: {str(e)}")


async def process_maturity_analysis_background(
    job_id: str,
    input_path: str,
    output_path: str,
    report_year: int,
    report_month: int,
    exchange_rate: float,
    input_header_start: int,
    input_data_start: int
):
    """Background task for maturity analysis processing"""
    try:
        jobs[job_id].status = "processing"

        start_time = time.perf_counter()
        result = maturity_processor.process_file(
            source_file_path=input_path,
            output_file_path=output_path,
            report_year=report_year,
            report_month=report_month,
            exchange_rate=exchange_rate,
            input_header_start=input_header_start,
            input_data_start=input_data_start
        )
        end_time = time.perf_counter()

        jobs[job_id].completed_at = datetime.now()
        jobs[job_id].result = result
        jobs[job_id].result["processing_time"] = end_time - start_time

        if result["success"]:
            jobs[job_id].status = "completed"
        else:
            jobs[job_id].status = "failed"
            jobs[job_id].error = result.get("error")

    except Exception as e:
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(e)
        jobs[job_id].completed_at = datetime.now()
        print(f"Maturity analysis error for job {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()


@app.post("/upload-maturity-analysis", response_model=ProcessingResponse)
async def upload_maturity_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_year: int = Form(...),
    report_month: int = Form(...),
    exchange_rate: float = Form(1.0),
    input_header_start: int = Form(8),
    input_data_start: int = Form(9)
):
    """Upload and process Excel file for maturity analysis report.

    The report date (year + month) is the reference point for year bucketing.
    Year 1 = payments in the 12 months after the report date.
    Target currency is taken from "Company Currency" field in the source data.
    """

    # Debug logging
    print(f"Received maturity analysis request - year: {report_year}, month: {report_month}")

    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")

    # Validate report month
    if not 1 <= report_month <= 12:
        raise HTTPException(status_code=400, detail="Report month must be between 1 and 12")

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Clean up old files
    cleanup_old_files()

    try:
        # Save uploaded file
        input_path = UPLOAD_DIR / f"{job_id}_input_{file.filename}"
        output_path = UPLOAD_DIR / f"{job_id}_output_maturity_analysis.xlsx"

        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Create job status
        jobs[job_id] = JobStatus(
            job_id=job_id,
            status="pending",
            created_at=datetime.now()
        )

        # Start background processing
        background_tasks.add_task(
            process_maturity_analysis_background,
            job_id,
            str(input_path),
            str(output_path),
            report_year,
            report_month,
            exchange_rate,
            input_header_start,
            input_data_start
        )

        return ProcessingResponse(
            success=True,
            message="File uploaded successfully. Maturity analysis processing started.",
            job_id=job_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/download-maturity-analysis/{job_id}")
async def download_maturity_analysis(job_id: str):
    """Download processed maturity analysis file"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_path = UPLOAD_DIR / f"{job_id}_output_maturity_analysis.xlsx"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        path=str(output_path),
        filename=f"maturity_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


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
        # Also clean up completed jobs older than 1 hour
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


# Mount static files for Vue.js frontend (must be after API routes)
def get_frontend_path():
    """Get the frontend directory path, handling PyInstaller executable"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable - frontend is in _internal
        base_path = Path(sys.executable).parent / "_internal"
    else:
        # Running as script
        base_path = Path(__file__).parent.parent
    
    return base_path / "frontend-dist"

frontend_path = get_frontend_path()
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

def open_browser(url: str):
    """Open the default browser to the application"""
    print(f"Opening browser to: {url}")
    webbrowser.open(url)


def run_desktop_mode():
    """Run the application in desktop mode"""
    global DESKTOP_MODE
    DESKTOP_MODE = True
    
    host = "localhost"
    port = 5001
    
    print("=" * 60)
    print("CTR Mapper Desktop Application")
    print("=" * 60)
    print(f"Starting application on http://{host}:{port}")
    print("The application will open in your default browser...")
    print("Close this window to stop the application.")
    print("=" * 60)
    
    # Debug: Print current working directory and check frontend path
    print(f"Current working directory: {os.getcwd()}")
    frontend_path = get_frontend_path()
    print(f"Frontend path: {frontend_path}")
    print(f"Frontend exists: {frontend_path.exists()}")
    if frontend_path.exists():
        print(f"Frontend contents: {list(frontend_path.iterdir())}")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=lambda: threading.Timer(3600, cleanup_old_files).start())
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Open browser after a short delay
    url = f"http://{host}:{port}"
    browser_thread = threading.Timer(1.5, lambda: open_browser(url))
    browser_thread.start()
    
    # Run the application
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")  # Keep console open to see error


def run_web_mode():
    """Run the application in web mode"""
    global DESKTOP_MODE
    DESKTOP_MODE = False
    
    host = "0.0.0.0"
    port = 8000
    
    print("=" * 60)
    print("CTR Mapper Web Application")
    print("=" * 60)
    print(f"Starting server on http://{host}:{port}")
    print("Access the application via web browser")
    print("API documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    # Run the application
    if "--reload" in sys.argv:
        uvicorn.run("app:app", host=host, port=port, reload=True)
    else:
        uvicorn.run(app, host=host, port=port, reload=False)


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="CTR Mapper Application")
    parser.add_argument("--desktop", action="store_true", help="Run in desktop mode")
    args = parser.parse_args()
    
    # Check if running as executable (PyInstaller sets sys.frozen)
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