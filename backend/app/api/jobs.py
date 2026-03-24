from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import asyncio

from app.core.database import get_db
from app.schemas.job import JobCreate, JobResponse
from app.models.job import CollectionJob
from app.services.collection_service import CollectionService
from app.core.websocket_manager import manager

router = APIRouter(prefix="/jobs", tags=["jobs"])

async def run_collection_job(job_id: UUID, device_filter: str):
    """Background task for metric collection"""
    import traceback
    from sqlalchemy import select, update
    from app.core.database import AsyncSessionLocal
    
    print(f"[BACKGROUND] Starting collection job {job_id}")
    
    try:
        async with AsyncSessionLocal() as db:
            # Update job status to running
            await db.execute(
                update(CollectionJob)
                .where(CollectionJob.id == job_id)
                .values(status="running", started_at=datetime.now())
            )
            await db.commit()
            print(f"[BACKGROUND] Job {job_id} status updated to running")
            
            # Progress callback
            async def progress_callback(message: str):
                print(f"[PROGRESS] {message}")
                await manager.broadcast_progress(job_id, message)
            
            # Run collection
            collection_service = CollectionService()
            print(f"[BACKGROUND] Starting metric collection...")
            result = await collection_service.collect_all_metrics(db, device_filter, progress_callback)
            print(f"[BACKGROUND] Collection result: {result}")
            
            # Update job status to completed
            await db.execute(
                update(CollectionJob)
                .where(CollectionJob.id == job_id)
                .values(status="completed", completed_at=datetime.now())
            )
            await db.commit()
            
            await manager.broadcast_progress(job_id, "Collection completed")
            print(f"[BACKGROUND] Job {job_id} completed successfully")
            
    except Exception as e:
        print(f"[BACKGROUND ERROR] Job {job_id} failed: {str(e)}")
        traceback.print_exc()
        
        try:
            async with AsyncSessionLocal() as db:
                # Update job status to failed
                await db.execute(
                    update(CollectionJob)
                    .where(CollectionJob.id == job_id)
                    .values(status="failed", completed_at=datetime.now(), error_message=str(e))
                )
                await db.commit()
                
                await manager.broadcast_progress(job_id, f"Collection failed: {str(e)}")
        except Exception as inner_e:
            print(f"[BACKGROUND ERROR] Failed to update job status: {inner_e}")

@router.post("/collect", response_model=JobResponse, status_code=202)
async def trigger_collection(
    job_create: JobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Trigger metric collection job"""
    # Create job record
    job = CollectionJob(
        job_type="metric_collection",
        status="pending",
        device_filter=job_create.device_filter
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Start background task using asyncio
    asyncio.create_task(run_collection_job(job.id, job_create.device_filter))
    
    return job

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get job status"""
    from sqlalchemy import select
    
    result = await db.execute(select(CollectionJob).where(CollectionJob.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job
