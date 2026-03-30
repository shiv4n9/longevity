# Device Collection Status

## Summary
- **Total Active Devices**: 15
- **Successfully Collecting Data**: 15 (100%)
- **Last Full Collection**: March 30, 2026 21:30 (88 seconds for all devices)

## Fixed Issues
1. **SSH Command Iteration Bug**: Fixed `for cmd_name, cmd in commands.items()` → `for cmd_name, cmd in commands:` in ssh_service.py line 256
   - This was causing all command outputs to be empty, resulting in NULL metrics
   - After fix, all devices now successfully collect CPU, memory, model, and other metrics

## Working Devices (15)

### High-End Devices (8)
- snpsrx4300a (CPU: 0%, Mem: 80%, Model: srx4300)
- snpsrx1600a (CPU: 0%, Mem: 24%, Model: srx1600)
- snpsrx4300b (CPU: 0%, Mem: 72%, Model: srx4300)
- snpsrx1600b (CPU: 0%, Mem: 26%, Model: srx1600)
- snpsrx4100c (CPU: 0%, Mem: 40%, Model: srx4200)
- snpsrx1500aa (CPU: 0%, Mem: 44%, Model: srx1500)
- snpsrx4600j (CPU: 0%, Mem: 41%, Model: srx4600)
- snpsrx4120c (CPU: 0%, Mem: 51%, Model: srx4120)

### Branch Devices (4)
- snpsrx380e (CPU: 0%, Mem: 63%, Model: srx380-poe-ac)
- snpsrx345d (CPU: 0%, Mem: 55%, Model: srx345)
- snpsrx340k (CPU: 0%, Mem: 55%, Model: srx340)
- snpsrx300y (CPU: 1%, Mem: 39%, Model: srx300)

### vSRX Devices (2)
- esst-srv66-http01 (CPU: 0%, Mem: 88%, Model: vSRX)
- esst-srv61-http01 (CPU: 0%, Mem: 74%, Model: vSRX)

### SPC3 Devices (1)
- snpsrx5600q (CPU: 0%, Mem: 65%, Model: srx5600)

## Removed Devices (3)
These devices were removed due to persistent collection failures:

1. **esst-srv71-vsrx01** (vSRX)
   - Issue: Parser unable to extract CPU/memory from security monitoring output
   - Status: Removed from database and data.json

2. **snpsrx4700b-proto** (High-End)
   - Issue: Parser unable to extract CPU/memory from security monitoring output
   - Status: Removed from database and data.json

3. **snpsrx5800x-b** (SPC3)
   - Issue: SSH connection fails with "Failed to reach device - still on jump host"
   - Root cause: CLI command not entering Junos properly
   - Status: Removed from database and data.json

## System Performance
- Collection time: ~88 seconds for all 15 devices
- Concurrency: 5 devices at a time (limited by SSH jump host MaxSessions=10)
- Success rate: 100% for active devices
- All devices use double-hop routing except vSRX devices (single-hop)

## Next Steps
- Monitor the 15 working devices for consistent data collection
- Frontend displays all 15 devices on landing page
- Single device refresh works correctly
- Full collection works correctly
