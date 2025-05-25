# Database Setup Guide for Futures Trading System

This guide explains how to set up the PostgreSQL database for the futures trading system.

## Database Users

The system uses two database users:

1. **trading_admin** - Administrative user with full privileges
   - Username: `trading_admin`
   - Password: `myAdmin4Tr4ding42!`
   - Permissions: SUPERUSER, CREATEDB, CREATEROLE

2. **trading_user** - Regular user for day-to-day operations
   - Username: `trading_user`
   - Password: `myData4Tr4ding42!`
   - Permissions: Connect, read/write data

## Setup Options

### Option 1: Using the Python Script (Recommended)

This is the easiest way to set up everything:

```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Run the setup script
python create_admin_and_db.py
```

You'll be prompted for the postgres user password. This script will:
- Create the trading_admin user with full privileges
- Create the trading_db database
- Set up the TimescaleDB extension
- Create the trading_user with appropriate permissions

### Option 2: Using SQL Scripts

If you prefer to use SQL directly:

1. Run the admin user creation script:
   ```bash
   # PowerShell
   .\create_admin_user.ps1
   
   # Or Command Prompt
   create_admin_user.bat
   ```

2. Connect to PostgreSQL as the trading_admin user and run:
   ```sql
   CREATE DATABASE trading_db;
   \c trading_db
   CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
   
   -- Create regular user
   CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';
   GRANT CONNECT ON DATABASE trading_db TO trading_user;
   GRANT USAGE ON SCHEMA public TO trading_user;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
   ```

### Option 3: Using pgAdmin

1. Open pgAdmin and connect as the postgres user
2. Execute the SQL in `create_admin_user.sql` to create the admin user
3. Create a new database named `trading_db` with owner `trading_admin`
4. Connect to the new database and create the TimescaleDB extension
5. Create the trading_user and grant appropriate permissions

## Initializing the Database

After creating the users and database, initialize the database structure:

```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Initialize the database using the admin user
python initialize_db.py
```

## Testing the Connection

To test the database connection:

```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Test the connection
python test_db_connection.py
```

## Troubleshooting

### TimescaleDB Extension

If you encounter errors related to the TimescaleDB extension:

1. Make sure TimescaleDB is installed on your PostgreSQL server
2. For Windows, you can install it using:
   ```
   choco install postgresql-timescaledb
   ```

### Permission Issues

If you encounter permission issues:

1. Make sure the trading_admin user has SUPERUSER privileges
2. Try connecting directly as the postgres user and granting permissions manually

### Connection Issues

If you can't connect to the database:

1. Verify PostgreSQL is running
2. Check that the host and port are correct in the .env file
3. Ensure the passwords are correct

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
DB_INIT_MODE=False
```

You can modify these in the `.env` file if needed.