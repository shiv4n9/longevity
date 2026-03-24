#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Starting Longevity Dashboard System                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Start PostgreSQL
echo "[1/3] Starting PostgreSQL database..."
docker-compose up -d postgres
sleep 5

# Start Backend
echo ""
echo "[2/3] Starting Backend API..."
echo "  → Jump Host: ttbg-shell012.juniper.net"
echo "  → API will be available at: http://localhost:8000"
echo ""

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

cd backend
source venv/bin/activate

# Set environment variables explicitly
export JUMP_HOST="ttbg-shell012.juniper.net"
export JUMP_HOST_USERNAME="sshivang"
export JUMP_HOST_PASSWORD="03Juniper@2026"
export SSH_USERNAME="root"
export SSH_PASSWORD="Embe1mpls"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/longevity"

# Start backend in background
uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

sleep 5

# Check if backend started
if ps -p $BACKEND_PID > /dev/null; then
    echo "  ✓ Backend started (PID: $BACKEND_PID)"
else
    echo "  ✗ Backend failed to start. Check backend.log for errors."
    exit 1
fi

# Start Frontend
echo ""
echo "[3/3] Starting Frontend..."
echo "  → Frontend will be available at: http://localhost:3000"
echo ""

docker-compose up -d frontend
sleep 3

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✓ System Started!                          ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Frontend:  http://localhost:3000                             ║"
echo "║  Backend:   http://localhost:8000                             ║"
echo "║  API Docs:  http://localhost:8000/docs                        ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Logs:      tail -f backend.log                               ║"
echo "║  Stop:      ./STOP.sh                                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Backend PID: $BACKEND_PID" > .backend.pid
