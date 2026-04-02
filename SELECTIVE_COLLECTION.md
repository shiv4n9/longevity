# Selective Device Collection Feature

## Overview
Users can now select specific devices for metric collection instead of collecting from all devices at once.

## How to Use

### Step 1: Enable Selection Mode
1. On the devices landing page, click the **"☑ Select Devices"** button
2. The interface switches to selection mode

### Step 2: Select Devices
- Click on device cards to select/deselect them
- Selected devices show a green border and checkmark
- Or click **"Select All"** to select all visible devices
- Click **"Clear"** to deselect all

### Step 3: Fetch Metrics
- Click **"FETCH SELECTED (X)"** where X is the number of selected devices
- The system will collect metrics from only the selected devices
- Progress is shown for each device

### Step 4: Exit Selection Mode
- Click **"Cancel"** to exit selection mode without collecting
- Or collection automatically exits selection mode after completion

## UI Changes

### Normal Mode
- **"☑ Select Devices"** button - Enter selection mode
- **"FETCH ALL METRICS"** button - Collect from all devices

### Selection Mode
- **"Select All (X)"** button - Select all filtered devices
- **"Clear"** button - Deselect all devices
- **"FETCH SELECTED (X)"** button - Collect from selected devices (disabled if none selected)
- **"Cancel"** button - Exit selection mode

### Device Cards in Selection Mode
- Checkbox in top-right corner
- Green border when selected
- Click anywhere on card to toggle selection
- Clicking doesn't navigate to device detail view

## Benefits

1. **Faster Collection**: Only collect from devices you need
2. **Targeted Updates**: Update specific devices without affecting others
3. **Bandwidth Efficient**: Reduce SSH connections and network traffic
4. **Flexible**: Select any combination of devices across types

## Technical Details

### Frontend State
- `selectionMode` (boolean): Whether selection mode is active
- `selectedDevices` (Set): Set of selected device names

### Collection Process
- Devices are collected in parallel (up to 5 concurrent connections)
- Progress shows overall status
- WebSocket connection tracks job completion
- Metrics automatically reload after all devices complete

### API Calls
Selected devices trigger a single API call:
```javascript
POST /api/v1/jobs/collect
{
  "device_names": ["snpsrx4300a", "snpsrx380e", "snpsrx345d"]
}
```

The backend handles parallel collection with a semaphore limiting to 5 concurrent SSH connections to prevent overwhelming the jump host.

## Example Use Cases

1. **Quick Check**: Select 2-3 critical devices for rapid status check
2. **Troubleshooting**: Collect from specific devices showing issues
3. **Platform Testing**: Select all devices of one platform (e.g., all SRX4300)
4. **Staged Updates**: Update devices in groups (e.g., test devices first, then production)

## Keyboard Shortcuts (Future Enhancement)
- `Ctrl+A` - Select all
- `Escape` - Exit selection mode
- `Enter` - Fetch selected
