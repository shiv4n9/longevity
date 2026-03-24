from fastapi import WebSocket
from typing import Dict, Set
from uuid import UUID
from datetime import datetime
import json

class WebSocketManager:
    """Manager for WebSocket connections and broadcasting"""
    
    def __init__(self):
        # Map job_id to set of connected websockets
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
    
    async def connect(self, job_id: UUID, websocket: WebSocket):
        """Register a new WebSocket connection for a job"""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
    
    def disconnect(self, job_id: UUID, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
    
    async def broadcast_progress(self, job_id: UUID, message: str):
        """Broadcast progress update to all connected clients for a job"""
        if job_id not in self.active_connections:
            return
        
        progress_data = {
            "job_id": str(job_id),
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_json(progress_data)
            except:
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(job_id, ws)

# Global manager instance
manager = WebSocketManager()
