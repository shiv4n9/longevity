from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional

from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate

class DeviceService:
    """Service for device management operations"""
    
    @staticmethod
    async def get_all_devices(db: AsyncSession) -> List[Device]:
        """Get all devices"""
        result = await db.execute(select(Device))
        return result.scalars().all()
    
    @staticmethod
    async def get_device_by_id(db: AsyncSession, device_id: UUID) -> Optional[Device]:
        """Get device by ID"""
        result = await db.execute(select(Device).where(Device.id == device_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_device_by_name(db: AsyncSession, name: str) -> Optional[Device]:
        """Get device by name"""
        result = await db.execute(select(Device).where(Device.name == name))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_device(db: AsyncSession, device: DeviceCreate) -> Device:
        """Create a new device"""
        db_device = Device(**device.model_dump())
        db.add(db_device)
        await db.commit()
        await db.refresh(db_device)
        return db_device
    
    @staticmethod
    async def update_device(db: AsyncSession, device_id: UUID, device_update: DeviceUpdate) -> Optional[Device]:
        """Update device"""
        result = await db.execute(select(Device).where(Device.id == device_id))
        db_device = result.scalar_one_or_none()
        
        if not db_device:
            return None
        
        update_data = device_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_device, field, value)
        
        await db.commit()
        await db.refresh(db_device)
        return db_device
    
    @staticmethod
    async def delete_device(db: AsyncSession, device_id: UUID) -> bool:
        """Delete device"""
        result = await db.execute(select(Device).where(Device.id == device_id))
        db_device = result.scalar_one_or_none()
        
        if not db_device:
            return False
        
        await db.delete(db_device)
        await db.commit()
        return True
    
    @staticmethod
    async def get_devices_by_type(db: AsyncSession, device_type: str) -> List[Device]:
        """Get devices filtered by type"""
        result = await db.execute(select(Device).where(Device.device_type == device_type))
        return result.scalars().all()
