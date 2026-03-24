# Single Device Dashboard - snpsrx4100c

## Overview
Extraordinary, focused dashboard designed exclusively for monitoring the snpsrx4100c High-End SRX device with maximum performance and visual impact.

## Key Features

### 🎯 Single Device Focus
- **Device**: snpsrx4100c (High-End SRX4200)
- **Optimized**: Only collects data from one device for fastest performance
- **Expected Collection Time**: 15-20 seconds (single device)

### 🎨 Extraordinary UI Design

#### Visual Elements
1. **Gradient Background**: Deep blue gradient for professional look
2. **Green Header**: Clean green theme matching corporate standards
3. **Large Device Title**: Prominent display of device name and type
4. **Status Badge**: Color-coded health indicator (Green/Orange/Red)

#### Metric Visualizations
1. **Gauge Charts**: Beautiful semi-circular gauges for CPU and Memory
   - Real-time percentage display
   - Color-coded (Green < 60%, Orange 60-80%, Red > 80%)
   - Smooth animations

2. **Big Numbers**: Large, easy-to-read session counts
   - Flow Sessions
   - CP Sessions
   - Global SHM percentage

3. **Status Indicators**: Clear health status for Core Dumps

4. **System Info Card**: Comprehensive device information
   - Hostname
   - Model
   - Junos Version
   - Routing Engine

### ⚡ Performance Optimizations

1. **Single Device Collection**: Only queries snpsrx4100c
2. **Efficient API Calls**: Minimal data transfer
3. **Auto-Refresh**: Optional 60-second auto-refresh
4. **Real-time Progress**: Live collection status updates
5. **Fast Rendering**: Optimized React components

### 🔄 Auto-Refresh Feature
- Toggle auto-refresh on/off
- Automatically collects metrics every 60 seconds
- Shows collection time for performance monitoring

## Performance Metrics

### Collection Time
- **Single Device**: ~15-20 seconds
- **Previous (4 devices)**: ~45-60 seconds
- **Improvement**: 3x faster

### Data Flow
1. User clicks "REFRESH NOW"
2. Backend connects: ttbg-shell012 → esst-srv2-arm → snpsrx4100c
3. Executes 5 commands in sequence
4. Parses and stores data
5. Dashboard updates with new metrics

## UI Components

### Header
- Brand name and tagline
- Auto-refresh toggle
- Refresh button

### Device Header
- Large device name (snpsrx4100c)
- Device type and model
- Health status badge

### Metrics Grid
- **System Information** (2-column card)
  - Hostname, Model, Junos Version, Routing Engine

- **CPU Usage** (Gauge)
  - Semi-circular gauge with percentage
  - Color-coded based on threshold

- **Memory Usage** (Gauge)
  - Semi-circular gauge with percentage
  - Color-coded based on threshold

- **Flow Sessions** (Big Number)
  - Current active connections

- **CP Sessions** (Big Number)
  - Control plane sessions

- **Core Dumps** (Status)
  - NONE (green) or DETECTED (red)

- **Global SHM** (Big Number)
  - Shared memory percentage

### Footer Info
- Last updated timestamp
- Collection time
- Device status

## Color Scheme

### Status Colors
- **Healthy**: #66bb6a (Green)
- **Warning**: #ffa726 (Orange)
- **Critical**: #ef5350 (Red)
- **Unknown**: #9e9e9e (Gray)

### Theme Colors
- **Primary**: #7cb342 to #558b2f (Green gradient)
- **Background**: #1e3c72 to #2a5298 (Blue gradient)
- **Cards**: White (#ffffff)
- **Text**: #2d3748 (Dark gray)
- **Secondary Text**: #718096 (Medium gray)

## Health Status Logic

### Healthy (Green)
- CPU < 60%
- Memory < 60%
- No core dumps

### Warning (Orange)
- CPU 60-80%
- OR Memory 60-80%

### Critical (Red)
- CPU > 80%
- OR Memory > 80%
- OR Core dumps detected

### Unknown (Gray)
- No data available
- Device unreachable

## Access

- **Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage

1. Open http://localhost:3000
2. Click "REFRESH NOW" to collect metrics
3. View real-time data with beautiful visualizations
4. Enable auto-refresh for continuous monitoring
5. Monitor collection time in footer

## Technical Details

### Frontend
- React with hooks
- SVG gauges for visualizations
- WebSocket for real-time updates
- Responsive design

### Backend
- FastAPI async operations
- Single device collection (highend filter)
- Double-hop SSH routing
- PostgreSQL storage

### Collection Commands
1. `show version | no-more`
2. `show chassis hardware | no-more`
3. `show security monitoring`
4. `show system core-dumps | no-more`
5. `request pfe execute command "sh arena" target fpc0`

## Future Enhancements

1. Historical data charts
2. Alert thresholds configuration
3. Export metrics to CSV
4. Email notifications
5. Comparison with baseline
6. Predictive analytics

## Troubleshooting

### Dashboard shows "No Data"
- Click "REFRESH NOW" to collect metrics
- Check backend is running: `ps aux | grep uvicorn`
- Check device connectivity

### Slow collection
- Normal: 15-20 seconds for single device
- Check network latency to jump hosts
- Review backend.log for errors

### Auto-refresh not working
- Ensure checkbox is enabled
- Check browser console for errors
- Verify WebSocket connection

## Support

For issues:
- Check `backend.log` for detailed errors
- Verify device is reachable from esst-srv2-arm
- Review `DEVICE_STATUS.md` for connectivity details
