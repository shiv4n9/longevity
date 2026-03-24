# Longevity Dashboard - Quick Start Guide

## Prerequisites
- Docker Desktop (running)
- Python 3.14 with venv already set up

## How to Run

### Option 1: Using Start Script (Recommended)
```bash
./START.sh
```

This will:
1. Start PostgreSQL database
2. Start Backend API on port 8000
3. Start Frontend on port 3000

### Option 2: Manual Start

#### Start Database
```bash
docker-compose up -d postgres
```

#### Start Backend
```bash
cd backend
source venv/bin/activate
export JUMP_HOST="ttbg-shell012.juniper.net"
export JUMP_HOST_USERNAME="sshivang"
export JUMP_HOST_PASSWORD="03Juniper@2026"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Start Frontend (in another terminal)
```bash
docker-compose up -d frontend
```

## Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## How to Use

### 1. View Devices
Open http://localhost:3000 and you'll see the list of 4 devices:
- snpsrx4100c (High-End)
- snpsrx380e (Branch)
- esst-srv71-vsrx01 (vSRX)
- snpsrx5800x-b (SPC3)

### 2. Collect Metrics
Click the "Collect Metrics" button to start collecting data from all devices.

The system will:
- Connect to ttbg-shell012.juniper.net (jump host)
- SSH to each device
- Execute monitoring commands
- Parse and store results in PostgreSQL
- Display real-time progress via WebSocket

### 3. View Results
After collection completes, the metrics table will show:
- Hostname
- Model
- Junos Version
- CPU Usage
- Memory Usage
- Session Counts
- Core Dumps Status
- Global Data SHM %

## Stop the Application

```bash
./STOP.sh
```

Or manually:
```bash
# Stop backend (Ctrl+C in terminal)
# Stop containers
docker-compose down
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
tail -f backend.log

# Verify database is running
docker ps | grep postgres
```

### Frontend won't load
```bash
# Check if frontend container is running
docker ps | grep frontend

# Restart frontend
docker-compose restart frontend
```

### Collection fails
- Ensure you're connected to Juniper network/VPN
- Check jump host credentials in .env file
- View backend logs: `tail -f backend.log`

## Architecture

```
┌─────────────┐
│   Browser   │
│ (React UI)  │
└──────┬──────┘
       │ HTTP/WebSocket
       ↓
┌─────────────┐
│   FastAPI   │
│   Backend   │
└──────┬──────┘
       │
       ├─→ PostgreSQL (metrics storage)
       │
       └─→ SSH → ttbg-shell012 → Devices
```

## Files Overview

- `START.sh` - Start the entire system
- `STOP.sh` - Stop the entire system
- `.env` - Configuration (jump host, credentials)
- `backend/` - FastAPI application
- `frontend/` - React application
- `docker-compose.yml` - Container orchestration

## Next Steps

1. Run `./START.sh`
2. Open http://localhost:3000
3. Click "Collect Metrics"
4. View results in the table

For detailed documentation, see `DESIGN_DOC.md`
