# Database Setup Guide

This guide explains how to set up the PostgreSQL database for the futures trading system.

## Prerequisites

- PostgreSQL installed on your machine
- pgAdmin (optional but recommended)
- Access to the postgres superuser account

## Option 1: Using pgAdmin

1. Open pgAdmin and connect to your PostgreSQL server
2. Right-click on the server and select "Query Tool"
3. Execute the following SQL commands:

```sql
-- Create the trading_user
CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';

-- Create the trading_db database
CREATE DATABASE trading_db WITH OWNER = trading_user;

-- Connect to the trading_db database
-- (Close this query window and open a new one connected to trading_db)

-- Grant privileges to trading_user
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO trading_user;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Make trading_user a superuser (to create extensions)
ALTER USER trading_user WITH SUPERUSER;
```

## Option 2: Using the Provided Scripts

### PowerShell Script

1. Open PowerShell
2. Navigate to the project directory
3. Run the setup script:

```
.\setup_db.ps1
```

4. Enter the postgres user password when prompted

### Batch File

1. Open Command Prompt
2. Navigate to the project directory
3. Run the setup batch file:

```
setup_db.bat
```

4. Enter the postgres user password when prompted

## Verifying the Setup

After setting up the database, you can verify it by running the database setup script:

```
.\venv\Scripts\Activate.ps1
python setup_database.py
```

You should see the message: "[SUCCESS] Database ready for tick collection!"

## Troubleshooting

If you encounter any issues:

1. Make sure PostgreSQL is running
2. Verify that the postgres user password is correct
3. Check if TimescaleDB extension is installed
4. Ensure that the trading_user has the necessary permissions

## Manual Database Creation Steps

If the scripts don't work, follow these steps manually:

1. Connect to PostgreSQL as the postgres user:
   ```
   psql -U postgres
   ```

2. Create the trading_user:
   ```sql
   CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';
   ```

3. Create the trading_db database:
   ```sql
   CREATE DATABASE trading_db WITH OWNER = trading_user;
   ```

4. Connect to the trading_db database:
   ```sql
   \c trading_db
   ```

5. Grant privileges:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
   GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user;
   ```

6. Enable TimescaleDB:
   ```sql
   CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
   ```

7. Make trading_user a superuser:
   ```sql
   ALTER USER trading_user WITH SUPERUSER;
   ```