# Device Status and Routing Configuration

## Current System Status

### ✅ Working Devices (3/4)

| Device | Type | Routing | Status | Notes |
|--------|------|---------|--------|-------|
| snpsrx380e | Branch SRX | Double-hop | ✅ Working | ttbg → esst-srv2-arm → device |
| snpsrx4100c | High-End SRX | Double-hop | ✅ Working | ttbg → esst-srv2-arm → device |
| snpsrx5800x-b | SPC3 | Double-hop | ✅ Working | ttbg → esst-srv2-arm → device |
| esst-srv71-vsrx01 | vSRX | Single-hop | ❌ Unreachable | Device is down or not accessible |

### Collection Performance

- **Expected Time**: 45-60 seconds for 3 working devices
- **Routing**: Intelligent routing based on device configuration
- **Concurrency**: All devices collected in parallel

## Routing Modes

### Double-Hop Routing
```
User → ttbg-shell012 → esst-srv2-arm → Device
```
- Used for: snpsrx380e, snpsrx4100c, snpsrx5800x-b
- These devices are accessible from esst-srv2-arm

### Single-Hop Routing
```
User → ttbg-shell012 → Device
```
- Configured for: esst-srv71-vsrx01
- Direct connection from ttbg-shell012 to device
- Currently not working because device is unreachable

## Device Connectivity Test Results

### From ttbg-shell012:
- ✅ snpsrx380e: Reachable via esst-srv2-arm
- ✅ snpsrx4100c: Reachable via esst-srv2-arm
- ✅ snpsrx5800x-b: Reachable via esst-srv2-arm
- ❌ esst-srv71-vsrx01: NOT reachable (100% packet loss)

### From esst-srv2-arm:
- ✅ snpsrx380e: Reachable (0% packet loss)
- ✅ snpsrx4100c: Reachable (0% packet loss)
- ✅ snpsrx5800x-b: Reachable (0% packet loss)
- ❌ esst-srv71-vsrx01: NOT reachable (100% packet loss)

## Troubleshooting esst-srv71-vsrx01

### Issue
Device is not responding to ping from either jump host:
- ttbg-shell012 → esst-srv71-vsrx01: 100% packet loss
- esst-srv2-arm → esst-srv71-vsrx01: No route to host

### Possible Causes
1. Device is powered off
2. Device is on a different network segment
3. Firewall rules blocking access
4. Device management interface (fxp0) is down
5. Network connectivity issue

### Resolution Steps
1. Verify device is powered on
2. Check physical network connectivity
3. Verify device management IP: 10.204.134.201
4. Check if device is accessible from a different jump host
5. Verify firewall rules allow SSH from jump hosts
6. Check device console for errors

## How to Add/Modify Device Routing

### 1. Update data.json
```json
{
    "name": "device-name",
    "vm": "device-hostname.englab.juniper.net",
    "type": "device-type",
    "routing": "single-hop"  // or "double-hop"
}
```

### 2. Update Database
```bash
python3 update_devices_routing.py
```

### 3. Restart Backend
```bash
./STOP.sh
./START.sh
```

## System Architecture

### SSH Connection Flow

**Double-Hop (Most Devices):**
1. Connect to ttbg-shell012.juniper.net (credentials: sshivang/03Juniper@2026)
2. SSH to esst-srv2-arm (credentials: root/Embe1mpls)
3. SSH to target device (credentials: root/Embe1mpls)
4. Enter CLI mode
5. Execute commands
6. Collect output

**Single-Hop (esst-srv71-vsrx01):**
1. Connect to ttbg-shell012.juniper.net (credentials: sshivang/03Juniper@2026)
2. SSH directly to target device (credentials: root/Embe1mpls)
3. Enter CLI mode
4. Execute commands
5. Collect output

### Commands Executed on Each Device

1. `show version | no-more` - System information
2. `show chassis hardware | no-more` - Hardware details
3. `show security monitoring` - Performance metrics
4. `show system core-dumps | no-more` - Crash detection
5. `request pfe execute command "sh arena" target [fpc/fwdd]` - Memory analysis

## Dashboard Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Next Steps

1. **Investigate esst-srv71-vsrx01**: Work with network team to restore connectivity
2. **Monitor Working Devices**: Use dashboard to track performance
3. **Add More Devices**: Follow the routing configuration guide above
4. **Set Up Alerts**: Configure thresholds for CPU/Memory warnings

## Support

For issues or questions:
- Check `backend.log` for detailed error messages
- Review `DASHBOARD_GUIDE.md` for user instructions
- Consult `DESIGN_DOC.md` for architecture details
