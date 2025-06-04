-- PostgreSQL Database Initialization for PrivateGPT Auth Service v2.0
-- Sets up proper collation, extensions, and initial configuration

-- Create database with proper collation for legal text search
-- (This is already done by docker-entrypoint, but ensuring proper settings)

-- Enable extensions for better performance and security
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create custom collation for case-insensitive email searches
CREATE COLLATION IF NOT EXISTS email_ci (
    provider = icu,
    locale = 'und-u-ks-level2',
    deterministic = false
);

-- Set timezone to UTC for consistency
SET timezone = 'UTC';

-- Configure connection limits and security
ALTER DATABASE auth_db SET log_statement = 'mod';
ALTER DATABASE auth_db SET log_min_duration_statement = 1000;
ALTER DATABASE auth_db SET shared_preload_libraries = 'pg_stat_statements';

-- Create indexes for better performance (these will be created by SQLAlchemy models too)
-- Note: SQLAlchemy will create the actual tables and primary indexes

-- Performance tuning settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Security settings
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_lock_waits = on;

-- Reload configuration
SELECT pg_reload_conf(); 