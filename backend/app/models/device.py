from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base

class DeviceType(str, enum.Enum):
    VSRX = "vsrx"
    HIGHEND = "highend"
    BRANCH = "branch"
    SPC3 = "spc3"

class DeviceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    hostname = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)
    routing = Column(String(50), default="double-hop")  # "single-hop" or "double-hop"
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
