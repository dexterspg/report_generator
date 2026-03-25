from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProcessingRequest(BaseModel):
    """Request model for file processing"""

    input_header_start: int = Field(
        default=27, description="Row number where headers start (1-indexed)"
    )


class ProcessingResponse(BaseModel):
    """Response model for file processing"""

    success: bool
    message: str
    job_id: Optional[str] = None
    input_rows: Optional[int] = None
    output_rows: Optional[int] = None
    sheets: Optional[list] = None
    unmapped_accounts: Optional[list] = None
    missing_rate_currencies: Optional[list] = None
    warnings: Optional[list] = None
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
