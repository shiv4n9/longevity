from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import devices, metrics, jobs, websocket, test, demo

app = FastAPI(
    title="Longevity Dashboard API",
    description="Enterprise-grade network device monitoring system",
    version="2.0.0"
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
app.include_router(test.router, prefix="/api/v1")
app.include_router(demo.router, prefix="/api/v1")
app.include_router(websocket.router)

@app.get("/api/v1/health/live")
async def health_check():
    """Liveness probe"""
    return {"status": "healthy", "service": "longevity-dashboard"}

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🚀 Longevity Dashboard API starting...")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Longevity Dashboard API shutting down...")
