from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.services.metrics_service import MetricsService
from app.schemas.metric import MetricResponse, MetricWithDevice

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/latest", response_model=List[MetricWithDevice])
async def get_latest_metrics(db: AsyncSession = Depends(get_db)):
    """Get latest metrics for all devices"""
    return await MetricsService.get_latest_metrics(db)

@router.get("/device/{device_id}", response_model=List[MetricResponse])
async def get_device_metrics(
    device_id: UUID,
    limit: int = 1000,
    days: int = None,
    db: AsyncSession = Depends(get_db)
):
    """Get historical metrics for a specific device"""
    metrics = await MetricsService.get_metrics_by_device(db, device_id, limit, days)
    return metrics
