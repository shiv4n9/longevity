# Migration Guide: Legacy to v2.0

## Overview

This guide helps you transition from the legacy Flask/Excel system to the new FastAPI/PostgreSQL architecture.

## What's Changed

| Component | Legacy | New |
|-----------|--------|-----|
| Backend | Flask (app.py) | FastAPI (backend/app/) |
| Business Logic | Monolithic Longevity.py | Modular services |
| Storage | Excel file | PostgreSQL |
| SSH Execution | Sequential blocking | Async concurrent |
| Updates | Manual refresh | WebSocket real-time |
| Credentials | Hardcoded in data.json | Environment variables |

## Data Migration

The new system starts fresh with an empty database. Legacy Excel data can be imported if needed:

```python
# Optional: Import legacy Excel data
python scripts/import_legacy_data.py security_monitoring.xlsx
```

## Configuration Migration

Legacy `data.json` credentials are now in `.env`:

```bash
# Old: data.json
{
  "ssh-username": "root",
  "ssh-password": "Embe1mpls"
}

# New: .env
SSH_USERNAME=root
SSH_PASSWORD=Embe1mpls
```

## API Mapping

| Legacy Endpoint | New Endpoint | Method |
|----------------|--------------|--------|
| `/refresh?type=all` | `/api/v1/jobs/collect` | POST |
| `/latest-data` | `/api/v1/metrics/latest` | GET |
| `/core-dumps/<hostname>` | `/api/v1/metrics/device/{id}` | GET |

## Performance Improvements

- **Collection Time:** 5 minutes → <1 minute (10 devices)
- **Concurrency:** Sequential → Parallel (all devices at once)
- **Connection Overhead:** Eliminated via persistent pooling
- **Storage Bottleneck:** Excel file locking → PostgreSQL MVCC

## Rollback Plan

If issues arise, the legacy system remains available:

```bash
# Run legacy system
python app.py
```

Both systems can run simultaneously on different ports (5001 vs 8000).
