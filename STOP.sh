#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Stopping Longevity Dashboard System                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Stop Backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid | grep "Backend PID:" | cut -d' ' -f3)
    if [ ! -z "$BACKEND_PID" ]; then
        echo "[1/3] Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
        echo "  ✓ Backend stopped"
    fi
    rm .backend.pid
else
    echo "[1/3] Backend PID file not found, trying pkill..."
    pkill -f "uvicorn app.main:app"
fi

# Stop Docker containers
echo ""
echo "[2/3] Stopping Docker containers..."
docker-compose down

echo ""
echo "[3/3] Cleanup complete"
echo ""
echo "✓ System stopped successfully"
