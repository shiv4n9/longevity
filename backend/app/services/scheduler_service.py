"""
Background scheduler for automatic metric collection
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.services.collection_service import CollectionService
from app.core.database import get_db

logger = logging.getLogger("longevity.scheduler")


class SchedulerService:
    """Background scheduler for periodic metric collection"""
    
    def __init__(self, interval_minutes: int = 10):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.task: Optional[asyncio.Task] = None
        self.running = False
        
    async def collect_all_metrics(self):
        """Collect metrics from all active devices"""
        try:
            logger.info(f"🔄 Starting scheduled collection at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            async for db in get_db():
                collection_service = CollectionService()
                
                # Collect from all devices
                job = await collection_service.start_collection(db, device_filter="all")
                
                logger.info(f"✓ Scheduled collection completed (Job ID: {job.id})")
                break  # Only need one db session
                
        except Exception as e:
            logger.error(f"❌ Scheduled collection failed: {e}", exc_info=True)
    
    async def run(self):
        """Run the scheduler loop"""
        self.running = True
        logger.info(f"🚀 Auto-monitoring started - collecting metrics every {self.interval_minutes} minutes")
        logger.info(f"⏰ Next collection will run in {self.interval_minutes} minutes")
        
        while self.running:
            try:
                # Wait for the interval first
                await asyncio.sleep(self.interval_seconds)
                
                # Collect metrics
                if self.running:  # Check again in case we're shutting down
                    logger.info(f"⏰ {self.interval_minutes} minutes elapsed - triggering scheduled collection")
                    await self.collect_all_metrics()
                    logger.info(f"⏰ Next collection will run in {self.interval_minutes} minutes")
                    
            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Continue running even if one iteration fails
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    def start(self):
        """Start the scheduler in the background"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        if self.task is None or self.task.done():
            self.running = False  # Reset before starting
            self.task = asyncio.create_task(self.run())
            logger.info("Scheduler task created")
        else:
            logger.warning("Scheduler task exists but not running")
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            logger.info("Scheduler stopped")


# Global scheduler instance
scheduler = SchedulerService(interval_minutes=10)
