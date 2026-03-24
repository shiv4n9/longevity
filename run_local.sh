#!/bin/bash

echo "🚀 Running Longevity Dashboard locally (backend on host, DB in Docker)..."

# Start only PostgreSQL in Docker
echo "Starting PostgreSQL..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo "Virtual environment exists"
fi

echo ""
echo "✅ PostgreSQL is running in Docker"
echo ""
echo "To start the backend locally:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend"
echo "  npm install"
echo "  npm run dev"
echo ""
echo "Or run: docker-compose up -d frontend"
