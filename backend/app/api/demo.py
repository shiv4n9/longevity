from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import uuid4

from app.core.database import get_db
from app.models.device import Device
from app.models.metric import Metric

router = APIRouter(prefix="/demo", tags=["demo"])

@router.post("/seed-data")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """Seed database with demo metrics data"""
    from sqlalchemy import select
    
    # Get all devices
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    
    if not devices:
        return {"status": "error", "message": "No devices found. Run init.sql first."}
    
    # Create sample metrics for each device
    for device in devices:
        metric = Metric(
            device_id=device.id,
            timestamp=datetime.now(),
            model="SRX4100" if device.device_type == "highend" else "SRX380",
            junos_version="21.4R3.15",
            routing_engine="JUNOS Software Release [21.4R3.15]",
            cpu_usage=45,
            memory_usage=62,
            flow_session_current=125000,
            cp_session_current=98000,
            has_core_dumps=False,
            global_data_shm_percent=35,
            raw_data={"demo": True}
        )
        db.add(metric)
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Created demo metrics for {len(devices)} devices"
    }
