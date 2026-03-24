from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.services.device_service import DeviceService
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse

router = APIRouter(prefix="/devices", tags=["devices"])

@router.get("/", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all devices"""
    devices = await DeviceService.get_all_devices(db)
    return devices

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get device by ID"""
    device = await DeviceService.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.post("/", response_model=DeviceResponse, status_code=201)
async def create_device(device: DeviceCreate, db: AsyncSession = Depends(get_db)):
    """Register a new device"""
    existing = await DeviceService.get_device_by_name(db, device.name)
    if existing:
        raise HTTPException(status_code=400, detail="Device with this name already exists")
    
    return await DeviceService.create_device(db, device)

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device_update: DeviceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update device"""
    device = await DeviceService.update_device(db, device_id, device_update)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete device"""
    success = await DeviceService.delete_device(db, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
