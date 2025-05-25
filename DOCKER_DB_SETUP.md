# Docker TimescaleDB Setup Guide

This guide explains how to set up the database users and permissions for the futures trading system when using the TimescaleDB Docker container.

## Docker Container Information

Your TimescaleDB container is running with these settings:
- Container name: `timescaledb-container`
- Image: `timescale/timescaledb:latest-pg13`
- Port mapping: `0.0.0.0:5432->5432/tcp`
- Default postgres password: `mysecretpassword`

## Setting Up Database Users

### Option 1: Using the Python Script (Recommended)

The easiest way to set up everything is to use the provided Python script:

```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Run the Docker-specific setup script
python create_admin_docker.py
```

This script will:
- Connect to the Docker container using the default postgres password
- Create the trading_admin user with full privileges
- Create the trading_db database
- Set up the TimescaleDB extension
- Create the trading_user with appropriate permissions

### Option 2: Using psql Directly

You can also connect to the Docker container using psql:

```bash
# Connect to the Docker container
psql -h localhost -p 5432 -U postgres -d postgres
```

When prompted for the password, enter: `mysecretpassword`

Then run these SQL commands:

```sql
-- Create admin user
CREATE USER trading_admin WITH 
    PASSWORD 'myAdmin4Tr4ding42!'
    SUPERUSER
    CREATEDB
    CREATEROLE
    INHERIT
    LOGIN;

-- Create database
CREATE DATABASE trading_db WITH OWNER = trading_admin;

-- Connect to the new database
\c trading_db

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create regular user
CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';

-- Grant privileges
GRANT CONNECT ON DATABASE trading_db TO trading_user;
GRANT USAGE ON SCHEMA public TO trading_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO trading_user;
```

## Testing the Connection

After setting up the users and database, test the connection:

```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Test the connection
python test_db_connection.py
```

## Troubleshooting

### Connection Issues

If you can't connect to the Docker container:

1. Make sure the container is running:
   ```
   docker ps | findstr timescale
   ```

2. If the container is not running, start it:
   ```
   docker start timescaledb-container
   ```

3. Check the container logs for any errors:
   ```
   docker logs timescaledb-container
   ```

### Permission Issues

If you encounter permission issues:

1. Connect as the postgres user and check the roles:
   ```sql
   \du
   ```

2. Make sure the trading_admin user has SUPERUSER privileges:
   ```sql
   ALTER USER trading_admin WITH SUPERUSER;
   ```

## Environment Variables

The system uses these environment variables for database connections:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=myData4Tr4ding42!
POSTGRES_ADMIN_USER=trading_admin
POSTGRES_ADMIN_PASSWORD=myAdmin4Tr4ding42!
POSTGRES_DOCKER_PASSWORD=mysecretpassword
```

You can modify these in the `.env` file if needed.