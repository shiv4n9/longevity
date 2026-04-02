# Longevity Dashboard v2.0

Enterprise-grade network device monitoring system for Juniper SRX firewalls with real-time telemetry collection via SSH.

![Platform](https://img.shields.io/badge/Platform-Juniper%20SRX-green)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB)
![Database](https://img.shields.io/badge/Database-PostgreSQL-336791)

---

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Database](#database)
- [Troubleshooting](#troubleshooting)
- [Changelog](#changelog)

---

## Features

### Core Capabilities
- **Platform-Based Grouping**: Devices grouped by hardware platform (SRX4300, SRX1600, vSRX specs)
- **Selective Collection**: Choose specific devices for metric collection
- **Real-Time Updates**: WebSocket progress notifications during collection
- **Historical Metrics**: Time-series data with PostgreSQL partitioning and configurable time ranges
- **Core Dump Detection**: Visual display of core dump files with path information
- **Active/Inactive Indicators**: Visual status showing which devices are collecting data
- **Sub-Minute Collection**: Concurrent SSH to devices with connection pooling (5 concurrent max)
- **Double-Hop SSH**: Support for jump host routing (ttbg-shell012 → esst-srv2-arm → device)

### Device Support
- High-end SRX (4300, 4600, 1600, 1500, 4100, 4120)
- Branch SRX (300, 340, 345, 380)
- Virtual SRX (vSRX)
- SPC3 platforms (5600, 5800)

### Metrics Collected
- CPU Utilization (%)
- Memory Allocation (%)
- Active Flow Sessions
- Control Plane Sessions
- Global Shared Memory Usage (%)
- Core Dump Detection
- Junos Version
- Platform/Model Information

---

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI    │─────▶│ PostgreSQL  │
│  Frontend   │      │   Backend    │      │  Database   │
│  (Port 3000)│      │  (Port 8000) │      │ (Port 5432) │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  SSH Service │
                     │  (Paramiko)  │
                     └──────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Jump Host       │
                  │  ttbg-shell012   │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  SRX Devices     │
                  │  (15 devices)    │
                  └──────────────────┘
```

### Technology Stack
- **Frontend**: React 18, Vite, Recharts, Axios
- **Backend**: FastAPI, Python 3.11, Paramiko (SSH), SQLAlchemy
- **Database**: PostgreSQL 15 with time-series partitioning
- **Deployment**: Docker, Docker Compose, Nginx (production)

---

## Quick Start

### Prerequisites
- Docker Desktop (required)
- Git
- Network access to ttbg-shell012.juniper.net
- 4GB RAM minimum, 20GB disk space

### Installation (5 Minutes)

1. **Clone the repository:**
```bash
git clone https://github.com/shiv4n9/longevity.git
cd longevity
```

2. **Configure environment:**
```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Update these values:
SSH_USERNAME=your_username
SSH_PASSWORD=your_password
POSTGRES_PASSWORD=secure_password
```

3. **Configure frontend API URL:**
```bash
# For local development
echo "VITE_API_URL=http://localhost:8000" > frontend/.env

# For server deployment
echo "VITE_API_URL=http://your-server-ip:8000" > frontend/.env
```

4. **Deploy:**
```bash
chmod +x deploy.sh
./deploy.sh
# Choose option 1 for development or 2 for production
```

5. **Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Stopping the System
```bash
docker-compose down
```

---

## Deployment

### Development Deployment
```bash
./deploy.sh
# Choose option 1
```

### Production Deployment (with Nginx)
```bash
./deploy.sh
# Choose option 2
```

For detailed deployment instructions, see:
- **SERVER_SETUP.md** - Quick 5-minute setup guide
- **DEPLOYMENT_GUIDE.md** - Comprehensive production deployment

### Server Deployment (esst-srv2-arm)

1. SSH to server:
```bash
ssh your-username@esst-srv2-arm.englab.juniper.net
```

2. Install Docker Compose (if needed):
```bash
sudo pip3 install docker-compose
```

3. Clone and deploy:
```bash
git clone https://github.com/shiv4n9/longevity.git
cd longevity
./deploy.sh
```

### Auto-Start on Boot

Create systemd service:
```bash
sudo nano /etc/systemd/system/longevity.service
```

```ini
[Unit]
Description=Longevity Dashboard
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/longevity
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable longevity
sudo systemctl start longevity
```

---

## Usage

### Viewing Devices

The landing page shows device cards grouped by platform:
- Platform name (e.g., SRX4300, VSRX-16CPU-32G)
- Active device indicator (✓ green = active, ○ red = inactive)
- Real-time metrics: CPU, Memory, SHM, Core Dumps

### Collecting Metrics

**Option 1: Collect All Devices**
- Click "FETCH ALL METRICS" button
- Watch real-time progress via WebSocket

**Option 2: Collect Filtered Devices**
- Select device type from dropdown (HIGHEND, VSRX, BRANCH, SPC3)
- Click "FETCH [TYPE] METRICS"

**Option 3: Selective Collection**
1. Click "☑ Select Devices"
2. Click on devices to select them (green border = selected)
3. Click "FETCH SELECTED (X)"
4. Only selected devices will be collected

**Option 4: Single Device**
- Click on a device card
- Click "REFRESH NOW" in detail view
- Only that device will be polled

### Viewing Historical Data

1. Click on any device card
2. View telemetry history graph
3. Use time range dropdown to select period:
   - Past 24 Hours
   - Past 2 Days
   - Past 3 Days
   - Past Week
   - Past 2 Weeks
   - Past Month

### Core Dump Detection

When core dumps are detected:
1. Device card shows "CORES: YES" in red
2. Click on device to view details
3. Click "CORE DETECTED" link
4. Modal displays core dump files with:
   - File name
   - Full path on device
   - Date/time
   - Type (Packet Forwarding Engine, Routing Protocol Daemon, etc.)

---

## Configuration

### Adding New Devices

Edit `data.json`:
```json
{
  "name": "snpsrx4300c",
  "vm": "snpsrx4300c.englab.juniper.net",
  "type": "highend",
  "routing": "double-hop"
}
```

Run:
```bash
python add_new_devices.py
```

### Device Types
- `highend`: High-end SRX (4300, 4600, 1600, etc.)
- `branch`: Branch SRX (300, 340, 345, 380)
- `vsrx`: Virtual SRX
- `spc3`: SPC3-based SRX (5600, 5800)

### Routing Options
- `single-hop`: Direct SSH from ttbg-shell012 to device
- `double-hop`: SSH via jump host (ttbg-shell012 → esst-srv2-arm → device)

### Platform Grouping

**Physical SRX**: Platform = Model name (uppercase)
- Example: `model: "srx4200"` → Platform: `"SRX4200"`

**vSRX**: Platform = Routing Engine specification
- Example: `routing_engine: "VSRX-16CPU-32G memory"` → Platform: `"VSRX-16CPU-32G memory"`

---

## API Documentation

### Devices API

```bash
# List all devices
GET /api/v1/devices/

# Get device by ID
GET /api/v1/devices/{device_id}
```

### Metrics API

```bash
# Get latest metrics for all devices
GET /api/v1/metrics/latest

# Get historical metrics for a device
GET /api/v1/metrics/device/{device_id}
```

### Jobs API

```bash
# Collect all devices
POST /api/v1/jobs/collect
{
  "device_filter": "all"
}

# Collect by device type
POST /api/v1/jobs/collect
{
  "device_filter": "highend"
}

# Collect single device
POST /api/v1/jobs/collect
{
  "device_name": "snpsrx4300a"
}

# Collect selected devices
POST /api/v1/jobs/collect
{
  "device_names": ["snpsrx4300a", "snpsrx380e", "snpsrx345d"]
}

# Get job status
GET /api/v1/jobs/{job_id}
```

### WebSocket

```javascript
// Connect to job progress
ws://localhost:8000/ws/{job_id}

// Receive progress messages
{
  "message": "Connecting to snpsrx4300a...",
  "timestamp": "2026-04-03T10:30:00Z"
}
```

---

## Database

### Schema

**Devices Table:**
- `id` (UUID)
- `name` (device hostname)
- `hostname` (FQDN)
- `device_type` (highend/branch/vsrx/spc3)
- `status` (active/inactive)
- `routing` (single-hop/double-hop)

**Metrics Table (Partitioned by Month):**
- `id` (bigint)
- `device_id` (UUID, foreign key)
- `timestamp` (timestamptz)
- `platform` (computed: model or routing_engine)
- `model` (from show version)
- `junos_version`
- `routing_engine` (from show chassis hardware)
- `cpu_usage` (%)
- `memory_usage` (%)
- `flow_session_current`
- `cp_session_current`
- `has_core_dumps` (boolean)
- `global_data_shm_percent` (%)
- `raw_data` (JSONB - contains core_dumps_output)

### Viewing Data

```bash
# Use provided script
bash view_database.sh

# Or manually
docker exec -it longevity-db psql -U postgres -d longevity
```

### Database Maintenance

```bash
# Check database size
docker exec longevity-db psql -U postgres -d longevity -c "SELECT pg_size_pretty(pg_database_size('longevity'));"

# Vacuum database
docker exec longevity-db psql -U postgres -d longevity -c "VACUUM ANALYZE;"

# View metrics count
docker exec longevity-db psql -U postgres -d longevity -c "SELECT COUNT(*) FROM metrics;"
```

### Backup & Restore

```bash
# Backup
docker exec longevity-db pg_dump -U postgres longevity | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip < backup_20260403.sql.gz | docker exec -i longevity-db psql -U postgres -d longevity
```

---

## Troubleshooting

### Docker Issues

```bash
# Check Docker status
docker ps

# Check logs
docker logs longevity-backend -f
docker logs longevity-frontend -f
docker logs longevity-db -f

# Restart containers
docker-compose restart

# Rebuild containers
docker-compose down
docker-compose up -d --build
```

### Backend Not Starting

```bash
# Check backend logs
tail -f backend.log

# Check if port 8000 is in use
lsof -ti:8000

# Kill process on port
kill $(lsof -ti:8000)
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec longevity-db psql -U postgres -d longevity -c "SELECT 1;"

# Check environment variables
docker exec longevity-backend env | grep POSTGRES
```

### SSH Connection Failures

```bash
# Test SSH to jump host
ssh your-username@ttbg-shell012.juniper.net

# Check SSH service logs
docker logs longevity-backend | grep -i ssh

# Verify credentials in .env
cat .env | grep SSH
```

### Frontend Can't Connect to Backend

```bash
# Check frontend environment
cat frontend/.env

# Should show correct API URL
# Fix and rebuild if wrong:
echo "VITE_API_URL=http://your-server-ip:8000" > frontend/.env
docker-compose up -d --build frontend
```

### Collection Failures

**Issue**: Devices showing as offline or NULL metrics

**Solutions**:
1. Check SSH connectivity from server to devices
2. Verify credentials in `.env`
3. Check backend logs for parsing errors
4. Ensure device is reachable from jump host

**Issue**: Collection takes too long

**Solutions**:
1. Use selective collection for specific devices
2. Check network latency to jump host
3. Verify SSH connection pooling is working

---

## Performance

- **Collection Time**: ~88 seconds for 15 devices (concurrent)
- **Concurrency**: 5 devices at a time (SSH jump host limit)
- **Single Device**: 2-3 seconds (with connection reuse)
- **API Response**: <500ms (p95)
- **Database**: Partitioned metrics table for efficient time-series queries

---

## Changelog

### v2.0 (Current)
- ✅ Platform-based device grouping
- ✅ Selective device collection with checkboxes
- ✅ Time range filter for historical graphs (24h, 2d, 3d, 7d, 14d, 30d)
- ✅ Core dump visualization with file paths
- ✅ Active/inactive device indicators
- ✅ IST timezone support
- ✅ Single device collection
- ✅ SSH connection pooling
- ✅ Database migration system
- ✅ Fixed SSH double-hop parsing issues
- ✅ Fixed dictionary iteration bug in SSH service
- ✅ Improved prompt detection for reliable device connections

### v1.0
- Initial FastAPI + React implementation
- PostgreSQL with partitioned metrics
- Docker containerization
- WebSocket real-time updates
- Double-hop SSH support

---

## System Status

### Working Devices (15/15)

**High-End (8)**: snpsrx4300a, snpsrx1600a, snpsrx4300b, snpsrx1600b, snpsrx4100c, snpsrx1500aa, snpsrx4600j, snpsrx4120c

**Branch (4)**: snpsrx380e, snpsrx345d, snpsrx340k, snpsrx300y

**vSRX (2)**: esst-srv66-http01, esst-srv61-http01

**SPC3 (1)**: snpsrx5600q

### Removed Devices (3)
- esst-srv71-vsrx01 (parsing issues)
- snpsrx4700b-proto (parsing issues)
- snpsrx5800x-b (SSH connection issues)

---

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Test SSH connection
python test_ssh_debug.py

# Test database
python backend/test_db.py

# Test single device collection
python test_single_hop.py
```

---

## Security

- Change default passwords in `.env`
- Use SSH keys instead of passwords (recommended)
- Restrict database access to localhost
- Keep Docker images updated
- Regular database backups
- Monitor logs for suspicious activity

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs: `docker logs longevity-backend`
3. Check database: `bash view_database.sh`
4. Verify network connectivity to devices

---

## License

Internal Juniper Networks project.

---

## Quick Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Update
git pull && docker-compose up -d --build

# Backup database
docker exec longevity-db pg_dump -U postgres longevity > backup.sql

# Check status
docker ps
```

---

**Frontend**: http://localhost:3000  
**Backend**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs
