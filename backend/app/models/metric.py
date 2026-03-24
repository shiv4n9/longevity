from sqlalchemy import Column, String, DateTime, Integer, BigInteger, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=func.now())
    model = Column(String(255))
    junos_version = Column(String(100))
    routing_engine = Column(String(255))
    cpu_usage = Column(Integer)
    memory_usage = Column(Integer)
    flow_session_current = Column(BigInteger)
    cp_session_current = Column(BigInteger)
    has_core_dumps = Column(Boolean, default=False)
    global_data_shm_percent = Column(Integer)
    raw_data = Column(JSONB)
