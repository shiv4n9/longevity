# Platform Grouping Feature

## Overview
Devices are now grouped by platform instead of showing individual device names. This provides a cleaner view when multiple devices share the same hardware platform.

## Platform Logic

### Physical SRX Devices
- Platform = Model name in uppercase (from `show version`)
- Example: `model: "srx4200"` → Platform: `"SRX4200"`
- Example: `model: "srx340"` → Platform: `"SRX340"`

### vSRX Devices
- Platform = Routing Engine specification (from `show chassis hardware`)
- Example: `routing_engine: "VSRX-16CPU-32G memory"` → Platform: `"VSRX-16CPU-32G memory"`
- This groups vSRX devices by their resource configuration

## Database Changes

### New Column
- Added `platform` column to `metrics` table
- Type: `VARCHAR(255)`
- Computed during metric collection based on device type

### Migration
Run the migration script to add the column and backfill existing data:
```bash
docker exec longevity-db psql -U postgres -d longevity -f /path/to/add_platform_column.sql
```

Or manually:
```sql
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS platform VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_metrics_platform ON metrics(platform);

UPDATE metrics 
SET platform = CASE 
    WHEN model = 'vSRX' THEN routing_engine
    WHEN model IS NOT NULL THEN UPPER(model)
    ELSE NULL
END
WHERE platform IS NULL;
```

## Backend Changes

### Collection Service (`backend/app/services/collection_service.py`)
- Computes platform value during metric collection
- Logic:
  ```python
  if device.device_type == "vsrx" and routing_engine:
      platform = routing_engine
  elif model:
      platform = model.upper()
  else:
      platform = None
  ```

### Models & Schemas
- `backend/app/models/metric.py`: Added `platform` column
- `backend/app/schemas/metric.py`: Added `platform` field to response

## Frontend Changes

### Device Grouping (`frontend/src/App.jsx`)
- Devices are grouped by platform
- Only one card shown per platform
- Prefers device with active metrics
- If multiple devices have same platform, shows alphabetically first

### Display
- **Card Header**: Shows platform name (e.g., "SRX4200", "VSRX-16CPU-32G memory")
- **Card Subtitle**: Shows active device name (e.g., "snpsrx4100c")
- **Detail View**: Shows platform name with active device subtitle

## Examples

### Before (Device Names)
- snpsrx4300a
- snpsrx4300b
- snpsrx1600a
- snpsrx1600b

### After (Platform Names)
- SRX4300 (active: snpsrx4300a)
- SRX1600 (active: snpsrx1600a)

### vSRX Example
- esst-srv61-http01 → Platform: "VSRX-16CPU-32G memory"
- esst-srv66-http01 → Platform: "VSRX-8CPU-16G memory" (if different specs)

## Benefits
1. Cleaner UI with fewer cards
2. Logical grouping by hardware platform
3. Easy to see which platforms are deployed
4. vSRX grouped by resource configuration
5. Platform data stored in DB for efficient querying
