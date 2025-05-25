-- Create the trading_user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_user') THEN
        CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';
    END IF;
END
$$;

-- Create the trading_db database if it doesn't exist
CREATE DATABASE trading_db WITH OWNER = trading_user;

-- We'll handle database connection separately in the scripts

-- Grant privileges to trading_user
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO trading_user;

-- Make sure trading_user can create extensions
ALTER USER trading_user WITH SUPERUSER;