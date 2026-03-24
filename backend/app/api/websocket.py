from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import UUID

from app.core.websocket_manager import manager

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: UUID):
    """WebSocket endpoint for real-time job progress updates"""
    await manager.connect(job_id, websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
