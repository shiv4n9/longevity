# Network Device Monitoring Dashboard - User Guide

## Overview
This dashboard provides real-time monitoring of Juniper SRX network devices, making it easy for anyone to understand device health and performance at a glance.

## Collection Time
- **Current Performance**: ~45-60 seconds for 3 devices (parallel collection)
- **Legacy Performance**: ~5 minutes for 10 devices (sequential)
- **Improvement**: ~5x faster with concurrent SSH connections

## Dashboard Features

### 1. Summary Statistics (Top Cards)
Four color-coded cards show the overall health at a glance:
- **Total Devices**: Total number of monitored devices
- **Healthy** (Green): Devices operating normally (CPU/Memory < 60%)
- **Warning** (Orange): Devices with elevated resource usage (60-80%)
- **Critical** (Red): Devices with high resource usage (>80%) or issues

### 2. Device Cards
Each device is displayed in an easy-to-read card format with:

#### Status Indicator
- 🟢 **Healthy**: Everything is normal
- 🟡 **Warning**: Resource usage is elevated, monitor closely
- 🔴 **Critical**: Immediate attention needed
- ⚪ **No Data**: Device is unreachable or data collection failed

#### Key Metrics Explained

**System Information:**
- 💾 **Junos Version**: Operating system version running on the device
- ⚙️ **Routing Engine**: Hardware model of the routing engine

**Performance Metrics:**
- 🖥️ **CPU Usage**: Processor utilization (0-100%)
  - Green: < 60% (Normal)
  - Orange: 60-80% (Warning)
  - Red: > 80% (Critical)

- 💾 **Memory Usage**: RAM utilization (0-100%)
  - Green: < 60% (Normal)
  - Orange: 60-80% (Warning)
  - Red: > 80% (Critical)

**Security & Sessions:**
- 🔄 **Flow Sessions**: Number of active network flows
- 🔐 **CP Sessions**: Number of active control plane sessions

**Health Indicators:**
- ⚠️ **Core Dumps**: System crash files
  - ✅ No: Device is stable
  - ❌ Yes: Device has experienced crashes (Critical)

- 📊 **Global SHM**: Shared memory usage percentage
  - Green: < 50% (Normal)
  - Orange: 50-70% (Warning)
  - Red: > 70% (Critical)

### 3. Controls

**Device Filter:**
- All Device Types: Show all devices
- vSRX (Virtual): Virtual SRX devices
- High-End SRX: Enterprise-grade devices (SRX4100, SRX5800)
- Branch SRX: Branch office devices (SRX380)
- SPC3: Devices with SPC3 cards

**Refresh Metrics Button:**
- Click to collect fresh data from all devices
- Shows collection time after completion
- Real-time progress updates during collection

### 4. Information Badges
- **Last updated**: Timestamp of the most recent data collection
- **Collection time**: How long the last collection took (in seconds)

## Understanding Device Health

### Healthy Device (🟢)
- CPU and Memory usage below 60%
- No core dumps present
- All systems operating normally
- **Action**: No action needed, continue monitoring

### Warning Device (🟡)
- CPU or Memory usage between 60-80%
- Elevated resource consumption
- **Action**: Monitor closely, investigate if usage continues to increase

### Critical Device (🔴)
- CPU or Memory usage above 80%
- Core dumps present (system crashes)
- High shared memory usage
- **Action**: Immediate investigation required

### No Data (⚪)
- Device is unreachable
- Network connectivity issues
- Device may be powered off
- **Action**: Check device connectivity and network path

## Device Types

### 💻 Virtual (vSRX)
- Virtual SRX devices running in virtualized environments
- Typically used for testing or small deployments

### 🏢 High-End (SRX4100, SRX5800)
- Enterprise-grade devices for data centers
- High throughput and session capacity
- Multiple routing engines for redundancy

### 🏪 Branch (SRX380)
- Branch office devices
- Compact form factor
- Suitable for small to medium offices

## Technical Details

### Architecture
- **Frontend**: React with real-time WebSocket updates
- **Backend**: FastAPI with async SSH operations
- **Database**: PostgreSQL with time-series metrics
- **SSH Path**: ttbg-shell012 → esst-srv2-arm → device (double-hop)

### Collection Process
1. User clicks "Refresh Metrics"
2. Backend initiates parallel SSH connections to all devices
3. Commands executed on each device:
   - `show version` - System information
   - `show chassis hardware` - Hardware details
   - `show security monitoring` - Performance metrics
   - `show system core-dumps` - Crash detection
   - `request pfe execute command "sh arena"` - Memory analysis
4. Data parsed and stored in database
5. Dashboard updates with new metrics

### Monitored Devices
- ✅ snpsrx380e (Branch SRX)
- ✅ snpsrx4100c (High-End SRX)
- ✅ snpsrx5800x-b (High-End SRX with SPC3)
- ❌ esst-srv71-vsrx01 (Currently unreachable)

## Troubleshooting

### "No Data" for a Device
- Check if device is powered on
- Verify network connectivity to esst-srv2-arm
- Check SSH credentials
- Review backend logs: `tail -f backend.log`

### Slow Collection
- Normal collection time: 45-60 seconds for 3 devices
- If slower, check network latency to jump hosts
- Verify devices are responding to SSH

### Connection Errors
- Ensure Docker is running
- Verify backend is running: `ps aux | grep uvicorn`
- Check database is accessible: `docker ps | grep longevity-db`

## System Management

### Start System
```bash
./START.sh
```

### Stop System
```bash
./STOP.sh
```

### View Logs
```bash
tail -f backend.log
```

### Access Points
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Best Practices

1. **Regular Monitoring**: Refresh metrics every 5-10 minutes during normal operations
2. **Alert Thresholds**: Investigate when devices show Warning or Critical status
3. **Trend Analysis**: Compare metrics over time to identify patterns
4. **Proactive Maintenance**: Address warnings before they become critical
5. **Documentation**: Keep notes on recurring issues for each device

## Support

For technical issues or questions:
- Check backend logs for detailed error messages
- Review SSH connectivity to jump hosts
- Verify device accessibility from esst-srv2-arm
- Consult the DESIGN_DOC.md for architecture details
