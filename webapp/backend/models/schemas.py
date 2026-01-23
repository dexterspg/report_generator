"""
Pydantic schemas for request/response models
"""

from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class ProcessingRequest(BaseModel):
    """Request parameters for file processing"""
    input_header_start: int = 27
    input_data_start: int = 28
    template_header_start: int = 1
    template_data_start: int = 2


class ProcessingResponse(BaseModel):
    """Response for file upload/processing"""
    success: bool
    message: str
    job_id: Optional[str] = None


class JobStatus(BaseModel):
    """Status of a processing job"""
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MaturityAnalysisRequest(BaseModel):
    """Request parameters for maturity analysis processing.

    Report year/month is the reference point for year bucketing.
    Year 1 = payments in the 12 months after the report date.
    Target currency is taken from "Company Currency" field in source data.
    """
    report_year: int
    report_month: int
    exchange_rate: float = 1.0
    input_header_start: int = 8
    input_data_start: int = 9
