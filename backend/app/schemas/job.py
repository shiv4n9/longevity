from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class JobCreate(BaseModel):
    device_filter: Optional[str] = "all"
    device_name: Optional[str] = None  # For single device collection

class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: str
    device_filter: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class JobProgress(BaseModel):
    job_id: UUID
    status: str
    progress: str
    device_name: Optional[str] = None
    current: Optional[int] = None
    total: Optional[int] = None
