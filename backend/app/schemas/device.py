from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    hostname: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., pattern="^(vsrx|highend|branch|spc3)$")
    status: str = Field(default="active", pattern="^(active|inactive|maintenance)$")

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    status: Optional[str] = None

class DeviceResponse(DeviceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
