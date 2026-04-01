-- Migration: Add platform column to metrics table
-- This adds a computed platform field that stores either the model (for physical SRX) 
-- or routing_engine (for vSRX) for easier querying and grouping

ALTER TABLE metrics ADD COLUMN IF NOT EXISTS platform VARCHAR(255);

-- Create index on platform for faster queries
CREATE INDEX IF NOT EXISTS idx_metrics_platform ON metrics(platform);

-- Backfill existing data with platform values
-- For vSRX devices (where model = 'vSRX'), use routing_engine
-- For physical SRX, use uppercase model
UPDATE metrics 
SET platform = CASE 
    WHEN model = 'vSRX' THEN routing_engine
    WHEN model IS NOT NULL THEN UPPER(model)
    ELSE NULL
END
WHERE platform IS NULL;
