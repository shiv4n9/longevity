#!/usr/bin/env python3
"""Update devices table to add routing column and set routing for existing devices"""
import asyncio
import sys
sys.path.insert(0, 'backend')

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def update_devices():
    async with AsyncSessionLocal() as db:
        # Add routing column if it doesn't exist
        try:
            await db.execute(text("""
                ALTER TABLE devices 
                ADD COLUMN IF NOT EXISTS routing VARCHAR(50) DEFAULT 'double-hop'
            """))
            print("✓ Added routing column to devices table")
        except Exception as e:
            print(f"Note: {e}")
        
        # Update esst-srv71-vsrx01 to use single-hop
        result = await db.execute(text("""
            UPDATE devices 
            SET routing = 'single-hop' 
            WHERE name = 'esst-srv71-vsrx01'
        """))
        await db.commit()
        print(f"✓ Updated esst-srv71-vsrx01 to single-hop routing ({result.rowcount} rows)")
        
        # Update other devices to use double-hop
        result = await db.execute(text("""
            UPDATE devices 
            SET routing = 'double-hop' 
            WHERE name != 'esst-srv71-vsrx01' AND (routing IS NULL OR routing = '')
        """))
        await db.commit()
        print(f"✓ Updated other devices to double-hop routing ({result.rowcount} rows)")
        
        # Show current device routing
        result = await db.execute(text("""
            SELECT name, hostname, device_type, routing 
            FROM devices 
            ORDER BY name
        """))
        devices = result.fetchall()
        
        print("\nCurrent device routing configuration:")
        print("-" * 80)
        for device in devices:
            print(f"  {device[0]:20} | {device[2]:10} | {device[3]}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(update_devices())
    print("\n✓ Database update complete!")
