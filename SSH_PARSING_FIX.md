# SSH Double-Hop and Parsing Fix

## Issues Found

### 1. Dictionary Iteration Bug (Line 241)
**Problem**: `for cmd_name, cmd in commands:` should be `commands.items()`
**Impact**: SSH commands failed with "too many values to unpack" error
**Status**: ✅ FIXED

### 2. Prompt Detection Too Permissive
**Problem**: `_read_until_prompt()` was matching `#` characters in banner text
**Impact**: Function returned before reaching actual shell prompt, causing commands to execute on wrong host
**Example**: Banner lines like `###############################################################################` were treated as prompts
**Status**: ✅ FIXED

**Solution**: Added validation to ensure prompts contain username/hostname patterns:
- Must have `@` character (user@host format)
- OR contain "root" or "sshivang" (known usernames)
- Prevents matching banner decoration lines

### 3. Insufficient Timeout After Password Entry
**Problem**: Ubuntu login banners are long and take time to display
**Impact**: Code moved to next step before prompt appeared
**Status**: ✅ FIXED

**Solution**: 
- Increased timeout from 10s to 20s after password entry
- Added 0.5s sleep after `_read_until_prompt()` to ensure stability

### 4. No Verification of Device Connection
**Problem**: Code didn't verify it reached the actual device before storing connection
**Impact**: Silently failed connections stored in pool, causing all subsequent commands to fail
**Status**: ✅ FIXED

**Solution**: Added verification after `cli` command:
```python
if "root>" not in cli_output and "root@" in cli_output and "~" in cli_output:
    raise Exception(f"Failed to reach device {device_name} - still on jump host")
```

## Root Cause Analysis

The parsing failures (NULL values in database) were caused by:

1. Commands executing on Linux jump host (esst-srv2-arm) instead of Junos devices
2. Parser expecting Junos output but receiving Linux error messages
3. Connection pool storing "successful" connections that were actually stuck on jump host

## Test Results

### Before Fix
```
=== MONITORING OUTPUT ===
show security monitoring
Command 'show' not found, but can be installed with:
apt install mailutils-mh
root@esst-srv2-arm:~#
```

### After Fix
```
=== MONITORING OUTPUT ===
show security monitoring 
                  Flow session   Flow session     CP session     CP session
FPC PIC CPU Mem        current        maximum        current        maximum
  0   0   0  40              0       10485760              0              0
root@snpsrx4100c>
```

## Files Modified

1. `backend/app/services/ssh_service.py`
   - Fixed dictionary iteration (line 241)
   - Improved `_read_until_prompt()` with username/hostname validation
   - Increased timeouts after password entry
   - Added device connection verification

## Impact

- ✅ Double-hop SSH now works correctly
- ✅ Commands execute on actual devices, not jump hosts
- ✅ Parsing will succeed and populate metrics correctly
- ✅ Single device collection ready for testing

## Next Steps

1. Test single device collection in frontend (click device → refresh)
2. Verify metrics are populated correctly
3. Test with different device types (highend, vsrx, spc3, branch)
