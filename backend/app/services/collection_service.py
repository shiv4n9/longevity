import asyncio
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.job import CollectionJob
from app.models.metric import Metric
from app.services.ssh_service import SSHService
from app.services.parser_service import ParserService
from app.services.command_service import CommandService
from app.core.config import get_settings

settings = get_settings()

class CollectionService:
    """Service for collecting metrics from devices with true concurrency"""
    
    def __init__(self):
        self.ssh_service = SSHService()
        self.parser = ParserService()
        self.command_service = CommandService()
    
    async def collect_device_metrics(
        self,
        device: Device,
        db: AsyncSession,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Collect metrics from a single device"""
        try:
            if progress_callback:
                await progress_callback(f"Connecting to {device.name}...")
            
            # Get device-specific commands
            commands = self.command_service.get_commands_for_device_type(device.device_type)
            
            # Execute commands via SSH with routing configuration
            routing = getattr(device, 'routing', 'double-hop')  # Default to double-hop if not set
            outputs = await self.ssh_service.execute_commands(
                device_hostname=device.hostname,
                device_username=settings.ssh_username,
                device_password=settings.ssh_password,
                commands=commands,
                device_name=device.name,
                routing=routing
            )
            
            if progress_callback:
                await progress_callback(f"Parsing data from {device.name}...")
            
            # Parse outputs
            hostname, model, junos = self.parser.parse_show_version(outputs.get('version', ''))
            routing_engine = self.parser.parse_chassis_hardware(outputs.get('chassis', ''))
            
            # Compute platform name
            # For vSRX: use routing_engine (e.g., "VSRX-16CPU-32G memory")
            # For physical SRX: use model in uppercase (e.g., "srx4200" -> "SRX4200")
            if device.device_type == "vsrx" and routing_engine:
                platform = routing_engine
            elif model:
                platform = model.upper()
            else:
                platform = None
            
            # Parse security monitoring based on device type
            if device.device_type == "spc3":
                security_data = self.parser.parse_security_monitoring_spc3(outputs.get('monitoring', ''))
            else:
                security_data = self.parser.parse_security_monitoring(outputs.get('monitoring', ''))
            
            has_cores, core_output = self.parser.parse_system_core_dumps(outputs.get('core_dumps', ''))
            global_shm = self.parser.parse_arena(outputs.get('arena', ''))
            
            # Save metrics (use first security data entry or defaults)
            sec_data = security_data[0] if security_data else {}
            
            metric = Metric(
                device_id=device.id,
                timestamp=datetime.now(),
                model=model,
                junos_version=junos,
                routing_engine=routing_engine,
                platform=platform,
                cpu_usage=sec_data.get('cpu'),
                memory_usage=sec_data.get('memory'),
                flow_session_current=sec_data.get('flow_session_current'),
                cp_session_current=sec_data.get('cp_session_current'),
                has_core_dumps=has_cores,
                global_data_shm_percent=global_shm,
                raw_data={"core_dumps_output": core_output if has_cores else None}
            )
            
            if progress_callback:
                await progress_callback(f"Completed {device.name}")
            
            return {"device": device.name, "status": "success", "metric": metric}
            
        except Exception as e:
            if progress_callback:
                await progress_callback(f"Failed {device.name}: {str(e)}")
            
            return {"device": device.name, "status": "failed", "error": str(e)}
    
    async def collect_all_metrics(
        self,
        db: AsyncSession,
        device_filter: Optional[str] = None,
        device_name: Optional[str] = None,
        device_names: Optional[list[str]] = None,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Collect metrics from devices concurrently (true parallelism).
        
        Args:
            device_filter: Filter by device type (highend, vsrx, branch, spc3, all)
            device_name: Filter by specific device name (e.g., snpsrx4100c)
            device_names: Filter by multiple device names (e.g., ['snpsrx4100c', 'snpsrx380e'])
            progress_callback: Callback for progress updates
        """
        from sqlalchemy import select
        
        # Get devices to process
        query = select(Device).where(Device.status == 'active')
        
        # Filter by multiple device names if provided
        if device_names:
            query = query.where(Device.name.in_(device_names))
        # Filter by specific device name if provided
        elif device_name:
            query = query.where(Device.name == device_name)
        # Otherwise filter by device type
        elif device_filter and device_filter != 'all':
            query = query.where(Device.device_type == device_filter)
        
        result = await db.execute(query)
        devices = result.scalars().all()
        
        if not devices:
            return {"status": "no_devices", "results": []}
        
        # Limit concurrency to 5 devices at a time to prevent SSH jump-host multiplexing limits (MaxSessions=10)
        sem = asyncio.Semaphore(5)
        
        async def bounded_collect(dev):
            async with sem:
                return await self.collect_device_metrics(dev, db, progress_callback)
                
        tasks = [
            bounded_collect(device)
            for device in devices
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and commit to db synchronously to avoid AsyncSession deadlock
        success_count = 0
        metrics_to_add = []
        
        for r in results:
            if isinstance(r, dict) and r.get("status") == "success":
                success_count += 1
                if "metric" in r:
                    metrics_to_add.append(r["metric"])
                    
        if metrics_to_add:
            db.add_all(metrics_to_add)
            await db.commit()
        
        return {
            "status": "completed",
            "total": len(devices),
            "success": success_count,
            "failed": len(devices) - success_count,
            "results": results
        }
