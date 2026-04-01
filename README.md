# Longevity Dashboard v2.0

Enterprise-grade network device monitoring system for Juniper SRX firewalls. Real-time telemetry collection via SSH with platform-based device grouping.

![Platform](https://img.shields.io/badge/Platform-Juniper%20SRX-green)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB)
![Database](https://img.shields.io/badge/Database-PostgreSQL-336791)

## Features

- **Platform-Based Grouping**: Devices grouped by hardware platform (SRX4300, SRX1600, vSRX specs)
- **Active/Inactive Indicators**: Visual status showing which devices are collecting data
- **Sub-Minute Collection**: Concurrent SSH to all devices with connection pooling
- **Real-Time Updates**: WebSocket progress notifications during collection
- **Historical Metrics**: Time-series data with PostgreSQL partitioning
- **Double-Hop SSH**: Support for jump host routing (ttbg-shell012 → esst-srv2-arm → device)
- **Device Type Support**: High-end SRX, Branch SRX, vSRX, and SPC3 platforms

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

## Quick Start

### Prerequisites

- **Docker Desktop** (required)
- **Git** (to clone the repository)
- **Network Access** to ttbg-shell012.juniper.net

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/shiv4n9/longevity.git
cd longevity
```

2. **Configure environment variables:**
```bash
# The .env file is already configured with default credentials
# Edit if you need to change SSH credentials or database settings
cat .env
```

3. **Start the system:**
```bash
bash start.sh
```

This will:
- Start PostgreSQL database in Docker
- Start the FastAPI backend (Python)
- Start the React frontend in Docker
- Apply database migrations automatically

4. **Access the application:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Stopping the System

```bash
bash STOP.sh
```

## Usage

### Viewing Devices

1. Open http://localhost:3000
2. You'll see device cards grouped by platform
3. Each card shows:
   - Platform name (e.g., SRX4300, SRX4200, VSRX-16CPU-32G memory)
   - Device name with status indicator:
     - ✓ Green = Active (collecting data)
     - ○ Red = Inactive (no recent data)
   - CPU, Memory, SHM, and Core Dumps metrics

### Collecting Metrics

**Option 1: Collect All Devices**
- Click "REFRESH NOW" button in the header
- Watch real-time progress as devices are polled

**Option 2: Collect Single Device**
- Click on a device card
- Click "REFRESH NOW" in the device detail view
- Only that device will be polled

### Viewing Historical Data

1. Click on any device card
2. View the telemetry history graph
3. See detailed metrics over time

## Configuration

### Adding New Devices

Edit `data.json` and add your device:

```json
{
  "name": "snpsrx4300c",
  "vm": "snpsrx4300c.englab.juniper.net",
  "type": "highend",
  "routing": "double-hop"
}
```

Then run:
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

## Database

### Viewing Data

Use the provided script:
```bash
bash view_database.sh
```

Options:
1. List all tables
2. View devices
3. View latest metrics (with platform)
4. View metrics count per device
5. Interactive psql session
6. View specific device metrics

### Manual Database Access

```bash
docker exec -it longevity-db psql -U postgres -d longevity
```

### Database Schema

**Devices Table:**
- `id` (UUID)
- `name` (device hostname)
- `hostname` (FQDN)
- `device_type` (highend/branch/vsrx/spc3)
- `status` (active/inactive)

**Metrics Table:**
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

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
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
# Test SSH connection to a device
python test_ssh_debug.py

# Test database connection
python backend/test_db.py

# Test single device collection
python test_single_hop.py
```

## API Documentation

### Devices API

```bash
# List all devices
curl http://localhost:8000/api/v1/devices/

# Get device by ID
curl http://localhost:8000/api/v1/devices/{device_id}
```

### Metrics API

```bash
# Get latest metrics for all devices
curl http://localhost:8000/api/v1/metrics/latest

# Get historical metrics for a device
curl http://localhost:8000/api/v1/metrics/device/{device_id}
```

### Jobs API

```bash
# Trigger collection for all devices
curl -X POST http://localhost:8000/api/v1/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{"device_filter": "all"}'

# Trigger collection for single device
curl -X POST http://localhost:8000/api/v1/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{"device_filter": "all", "device_name": "snpsrx4300a"}'

# Get job status
curl http://localhost:8000/api/v1/jobs/{job_id}
```

## Troubleshooting

### Docker not running
```bash
# Check Docker status
docker ps

# If error, start Docker Desktop application
```

### Backend not starting
```bash
# Check backend logs
tail -f backend.log

# Check if port 8000 is in use
lsof -ti:8000
```

### Database connection issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check database logs
docker logs longevity-db
```

### SSH connection failures
```bash
# Test SSH to jump host
ssh sshivang@ttbg-shell012.juniper.net

# Check SSH service logs in backend.log
tail -f backend.log | grep SSH
```

## Platform Grouping

Devices are grouped by platform for cleaner visualization:

### Physical SRX
Platform = Model name in uppercase (from `show version`)
- Example: `model: "srx4200"` → Platform: `"SRX4200"`

### vSRX
Platform = Routing Engine specification (from `show chassis hardware`)
- Example: `routing_engine: "VSRX-16CPU-32G memory"` → Platform: `"VSRX-16CPU-32G memory"`

This allows:
- Multiple devices with same platform (e.g., 4300a and 4300b) to be shown together
- vSRX devices to be grouped by resource configuration
- Clear indication of which device is active

## Performance

- **Collection Time**: ~88 seconds for 15 devices (concurrent)
- **Concurrency**: 5 devices at a time (SSH jump host limit)
- **API Response**: <500ms (p95)
- **Database**: Partitioned metrics table for efficient time-series queries

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Internal Juniper Networks project.

## Support

For issues or questions:
- Check the troubleshooting section above
- Review backend logs: `tail -f backend.log`
- Check database: `bash view_database.sh`
- Review documentation in `/docs` folder

## Changelog

### v2.0 (Current)
- Platform-based device grouping
- Active/inactive device indicators
- IST timezone support
- Single device collection
- SSH connection pooling
- Database migration system

### v1.0
- Initial FastAPI + React implementation
- PostgreSQL with partitioned metrics
- Docker containerization
- WebSocket real-time updates
