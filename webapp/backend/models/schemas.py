from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProcessingRequest(BaseModel):
    """Request model for file processing"""

    input_header_start: int = Field(
        default=27, description="Row number where headers start (1-indexed)"
    )
    input_data_start: int = Field(
        default=28, description="Row number where data starts (1-indexed)"
    )
    template_header_start: int = Field(
        default=1, description="Output header row (1-indexed)"
    )
    template_data_start: int = Field(
        default=2, description="Output data start row (1-indexed)"
    )


class ProcessingResponse(BaseModel):
    """Response model for file processing"""

    success: bool
    message: str
    job_id: Optional[str] = None
    input_rows: Optional[int] = None
    output_rows: Optional[int] = None
    file_size: Optional[int] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


class JobStatus(BaseModel):
    """Job status model"""

    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class FileInfo(BaseModel):
    """File information model"""

    filename: str
    size: int
    content_type: str
    upload_time: datetime
