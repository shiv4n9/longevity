-- Database initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    hostname VARCHAR(255) NOT NULL,
    device_type VARCHAR(50) NOT NULL CHECK (device_type IN ('vsrx', 'highend', 'branch', 'spc3')),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on device name for faster lookups
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);

-- Metrics table (will be partitioned)
CREATE TABLE IF NOT EXISTS metrics (
    id BIGSERIAL,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    model VARCHAR(255),
    junos_version VARCHAR(100),
    routing_engine VARCHAR(255),
    cpu_usage INTEGER,
    memory_usage INTEGER,
    flow_session_current BIGINT,
    cp_session_current BIGINT,
    has_core_dumps BOOLEAN DEFAULT FALSE,
    global_data_shm_percent INTEGER,
    raw_data JSONB,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create initial partition for current month
CREATE TABLE IF NOT EXISTS metrics_2026_03 PARTITION OF metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Create index on device_id and timestamp for faster queries
CREATE INDEX IF NOT EXISTS idx_metrics_device_timestamp ON metrics(device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC);

-- Collection jobs table
CREATE TABLE IF NOT EXISTS collection_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    device_filter VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON collection_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON collection_jobs(created_at DESC);

-- Insert sample devices from legacy data.json
INSERT INTO devices (name, hostname, device_type) VALUES
    ('snpsrx4100c', 'snpsrx4100c.englab.juniper.net', 'highend'),
    ('snpsrx380e', 'snpsrx380e.englab.juniper.net', 'branch'),
    ('esst-srv71-vsrx01', 'esst-srv71-vsrx01.englab.juniper.net', 'vsrx'),
    ('snpsrx5800x-b', 'snpsrx5800x-b.englab.juniper.net', 'spc3')
ON CONFLICT (name) DO NOTHING;
