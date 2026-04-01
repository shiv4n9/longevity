from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any

class MetricBase(BaseModel):
    model: Optional[str] = None
    junos_version: Optional[str] = None
    routing_engine: Optional[str] = None
    platform: Optional[str] = None
    cpu_usage: Optional[int] = None
    memory_usage: Optional[int] = None
    flow_session_current: Optional[int] = None
    cp_session_current: Optional[int] = None
    has_core_dumps: bool = False
    global_data_shm_percent: Optional[int] = None

class MetricCreate(MetricBase):
    device_id: UUID
    raw_data: Optional[Dict[str, Any]] = None

class MetricResponse(MetricBase):
    id: int
    device_id: UUID
    timestamp: datetime
    raw_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class MetricWithDevice(MetricResponse):
    device_name: str
    hostname: str
