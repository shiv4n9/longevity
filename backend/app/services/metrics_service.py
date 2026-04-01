from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.metric import Metric
from app.models.device import Device
from app.schemas.metric import MetricCreate, MetricWithDevice

class MetricsService:
    """Service for metrics operations"""
    
    @staticmethod
    async def create_metric(db: AsyncSession, metric: MetricCreate) -> Metric:
        """Create a new metric entry"""
        db_metric = Metric(**metric.model_dump())
        db.add(db_metric)
        await db.commit()
        await db.refresh(db_metric)
        return db_metric
    
    @staticmethod
    async def get_latest_metrics(db: AsyncSession) -> List[MetricWithDevice]:
        """Get latest metric for each device with device info"""
        # Subquery to get latest timestamp per device
        subq = (
            select(Metric.device_id, func.max(Metric.timestamp).label('max_ts'))
            .group_by(Metric.device_id)
            .subquery()
        )
        
        # Join to get full metric records
        query = (
            select(Metric, Device)
            .join(Device, Metric.device_id == Device.id)
            .join(subq, (Metric.device_id == subq.c.device_id) & (Metric.timestamp == subq.c.max_ts))
            .order_by(Device.name)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        metrics_with_devices = []
        for metric, device in rows:
            metric_dict = {
                "id": metric.id,
                "device_id": metric.device_id,
                "timestamp": metric.timestamp,
                "model": metric.model,
                "junos_version": metric.junos_version,
                "routing_engine": metric.routing_engine,
                "platform": metric.platform,
                "cpu_usage": metric.cpu_usage,
                "memory_usage": metric.memory_usage,
                "flow_session_current": metric.flow_session_current,
                "cp_session_current": metric.cp_session_current,
                "has_core_dumps": metric.has_core_dumps,
                "global_data_shm_percent": metric.global_data_shm_percent,
                "raw_data": metric.raw_data,
                "device_name": device.name,
                "hostname": device.hostname
            }
            metrics_with_devices.append(MetricWithDevice(**metric_dict))
        
        return metrics_with_devices
    
    @staticmethod
    async def get_metrics_by_device(
        db: AsyncSession,
        device_id: UUID,
        limit: int = 100
    ) -> List[Metric]:
        """Get metrics for a specific device"""
        query = (
            select(Metric)
            .where(Metric.device_id == device_id)
            .order_by(desc(Metric.timestamp))
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()
