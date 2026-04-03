import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import devices, metrics, jobs, websocket
from app.services.scheduler_service import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("longevity")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("🚀 Longevity Dashboard API starting...")
    logger.info("ℹ️  Auto-monitoring is OFF by default. Enable it from the dashboard.")
    
    yield
    
    # Stop the scheduler on shutdown if running
    if scheduler.running:
        await scheduler.stop()
    logger.info("👋 Longevity Dashboard API shutting down...")


app = FastAPI(
    title="Longevity Dashboard API",
    description="Enterprise-grade network device monitoring system",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/api/v1/health/live")
async def health_check():
    """Liveness probe"""
    return {"status": "healthy", "service": "longevity-dashboard"}


@app.get("/api/v1/scheduler/status")
async def scheduler_status():
    """Get scheduler status"""
    return {
        "running": scheduler.running,
        "interval_minutes": scheduler.interval_minutes,
        "task_active": scheduler.task is not None and not scheduler.task.done()
    }


@app.post("/api/v1/scheduler/start")
async def start_scheduler():
    """Start the automatic metric collection scheduler"""
    if scheduler.running:
        return {"message": "Scheduler is already running", "running": True}
    
    scheduler.start()
    logger.info("✓ Auto-monitoring started by user")
    return {"message": "Auto-monitoring started (10-minute interval)", "running": True}


@app.post("/api/v1/scheduler/stop")
async def stop_scheduler():
    """Stop the automatic metric collection scheduler"""
    if not scheduler.running:
        return {"message": "Scheduler is not running", "running": False}
    
    await scheduler.stop()
    logger.info("✓ Auto-monitoring stopped by user")
    return {"message": "Auto-monitoring stopped", "running": False}
