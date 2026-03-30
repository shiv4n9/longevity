#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Longevity Dashboard System Status Check               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Docker
echo "[1/5] Checking Docker..."
if docker info > /dev/null 2>&1; then
    echo "  ✓ Docker is running"
else
    echo "  ✗ Docker is NOT running"
    echo "  → Please start Docker Desktop first"
    echo ""
    exit 1
fi

# Check PostgreSQL
echo ""
echo "[2/5] Checking PostgreSQL..."
if docker ps | grep -q longevity-db; then
    echo "  ✓ PostgreSQL container is running"
    
    # Test database connection
    if docker exec longevity-db psql -U postgres -d longevity -c "SELECT COUNT(*) FROM devices;" > /dev/null 2>&1; then
        DEVICE_COUNT=$(docker exec longevity-db psql -U postgres -d longevity -t -c "SELECT COUNT(*) FROM devices;")
        echo "  ✓ Database is accessible (${DEVICE_COUNT} devices)"
    else
        echo "  ⚠ Database container running but not accessible"
    fi
else
    echo "  ✗ PostgreSQL container is NOT running"
    echo "  → Run: docker-compose up -d postgres"
fi

# Check Backend
echo ""
echo "[3/5] Checking Backend..."
if ps aux | grep -E "uvicorn.*app.main:app" | grep -v grep > /dev/null; then
    BACKEND_PID=$(ps aux | grep -E "uvicorn.*app.main:app" | grep -v grep | awk '{print $2}')
    echo "  ✓ Backend is running (PID: $BACKEND_PID)"
    
    # Test backend API
    if curl -s http://localhost:8000/api/v1/health/live | grep -q "healthy"; then
        echo "  ✓ Backend API is responding"
    else
        echo "  ⚠ Backend running but API not responding"
    fi
else
    echo "  ✗ Backend is NOT running"
    echo "  → Run: ./start.sh"
fi

# Check Frontend
echo ""
echo "[4/5] Checking Frontend..."
if docker ps | grep -q longevity-frontend; then
    echo "  ✓ Frontend container is running"
    
    # Test frontend
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "  ✓ Frontend is accessible"
    else
        echo "  ⚠ Frontend container running but not accessible"
    fi
else
    echo "  ✗ Frontend container is NOT running"
    echo "  → Run: docker-compose up -d frontend"
fi

# Check recent metrics
echo ""
echo "[5/5] Checking Recent Data Collection..."
if docker ps | grep -q longevity-db; then
    LATEST=$(docker exec longevity-db psql -U postgres -d longevity -t -c "SELECT MAX(collected_at) FROM metrics;" 2>/dev/null | xargs)
    if [ ! -z "$LATEST" ] && [ "$LATEST" != "" ]; then
        echo "  ✓ Last data collection: $LATEST"
        
        # Count devices with recent data
        DEVICES_WITH_DATA=$(docker exec longevity-db psql -U postgres -d longevity -t -c "SELECT COUNT(DISTINCT device_id) FROM metrics WHERE collected_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | xargs)
        echo "  → Devices with data in last hour: $DEVICES_WITH_DATA"
    else
        echo "  ⚠ No metrics data found"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  To start the system: ./start.sh                              ║"
echo "║  To stop the system:  ./STOP.sh                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
