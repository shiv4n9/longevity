#!/usr/bin/env python3
"""
Script to add new devices to the Longevity Dashboard database
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.device import Device
from app.core.config import get_settings

settings = get_settings()

async def add_devices():
    """Add devices from data.json to the database"""
    
    # Load devices from data.json
    with open('data.json', 'r') as f:
        data = json.load(f)
    
    devices_data = data.get('devices', [])
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get existing devices
        result = await session.execute(select(Device))
        existing_devices = {d.name: d for d in result.scalars().all()}
        
        added = 0
        updated = 0
        skipped = 0
        
        for device_data in devices_data:
            name = device_data['name']
            hostname = device_data['vm']
            device_type = device_data['type']
            routing = device_data.get('routing', 'double-hop')
            
            if name in existing_devices:
                # Update existing device
                device = existing_devices[name]
                device.hostname = hostname
                device.device_type = device_type
                device.routing = routing
                device.status = 'active'
                print(f"✓ Updated: {name} ({device_type}, {routing})")
                updated += 1
            else:
                # Add new device
                device = Device(
                    name=name,
                    hostname=hostname,
                    device_type=device_type,
                    status='active',
                    routing=routing
                )
                session.add(device)
                print(f"✓ Added: {name} ({device_type}, {routing})")
                added += 1
        
        await session.commit()
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Added: {added} devices")
        print(f"  Updated: {updated} devices")
        print(f"  Total in data.json: {len(devices_data)} devices")
        print(f"{'='*60}")
        
        # Show all devices
        result = await session.execute(select(Device).order_by(Device.name))
        all_devices = result.scalars().all()
        
        print(f"\nAll devices in database ({len(all_devices)}):")
        print(f"{'Name':<25} {'Type':<10} {'Routing':<12} {'Status'}")
        print(f"{'-'*60}")
        for d in all_devices:
            print(f"{d.name:<25} {d.device_type:<10} {d.routing:<12} {d.status}")

if __name__ == "__main__":
    print("Adding devices to Longevity Dashboard database...")
    print("="*60)
    asyncio.run(add_devices())
