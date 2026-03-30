import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import devices, metrics, jobs, websocket

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
    yield
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
    allow_credentials=True,
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
