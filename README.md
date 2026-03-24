# Longevity Dashboard v2.0

Enterprise-grade network device monitoring system built with FastAPI, React, and PostgreSQL.

## Architecture

- **Backend:** FastAPI with async SSH operations
- **Frontend:** React with WebSocket real-time updates
- **Database:** PostgreSQL with partitioned metrics table
- **Deployment:** Docker Compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Setup

1. Clone and configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

2. Start services:
```bash
docker-compose up -d
```

3. Access the application:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000 (after frontend setup)

### Local Development

Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Endpoints

### Devices
- `GET /api/v1/devices` - List all devices
- `POST /api/v1/devices` - Register new device
- `GET /api/v1/devices/{id}` - Get device details
- `PUT /api/v1/devices/{id}` - Update device
- `DELETE /api/v1/devices/{id}` - Delete device

### Metrics
- `GET /api/v1/metrics/latest` - Get latest metrics for all devices
- `GET /api/v1/metrics/device/{id}` - Get historical metrics

### Jobs
- `POST /api/v1/jobs/collect` - Trigger metric collection
- `GET /api/v1/jobs/{id}` - Get job status
- `WS /ws/{job_id}` - WebSocket for real-time progress

## Key Features

- **Sub-1-Minute Collection:** Async concurrent SSH to all devices
- **Real-time Updates:** WebSocket progress notifications
- **Persistent Connections:** Connection pooling eliminates handshake overhead
- **Scalable Storage:** PostgreSQL with time-series partitioning
- **Enterprise Ready:** Docker containerization, health checks, ACID compliance

## Migration from Legacy

The legacy Flask/Excel system is replaced entirely. Device configurations from `data.json` are migrated to PostgreSQL on first run.

## Success Metrics

- Collection time: ~5 minutes → <1 minute (10 devices)
- Concurrent monitoring: ~5 → 20+ devices
- API response time: <500ms (p95)
- System uptime: 99%
