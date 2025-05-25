# PowerShell script to create PostgreSQL user and database

# Set PostgreSQL connection parameters
$PGHOST = "localhost"
$PGPORT = "5432"
$PGUSER = "postgres"
$PGPASSWORD = Read-Host -Prompt "Enter postgres user password" -AsSecureString
$PGPASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($PGPASSWORD))

# Create trading_user
$createUserCmd = "psql -h $PGHOST -p $PGPORT -U $PGUSER -c ""CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';"""
Write-Host "Creating trading_user..."
$env:PGPASSWORD = $PGPASSWORD_PLAIN
Invoke-Expression $createUserCmd

# Create trading_db database
$createDbCmd = "psql -h $PGHOST -p $PGPORT -U $PGUSER -c ""CREATE DATABASE trading_db WITH OWNER = trading_user;"""
Write-Host "Creating trading_db database..."
Invoke-Expression $createDbCmd

# Grant privileges
$grantPrivilegesCmd = "psql -h $PGHOST -p $PGPORT -U $PGUSER -d trading_db -c ""GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user; GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user;"""
Write-Host "Granting privileges..."
Invoke-Expression $grantPrivilegesCmd

# Enable TimescaleDB extension
$enableExtensionCmd = "psql -h $PGHOST -p $PGPORT -U $PGUSER -d trading_db -c ""CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"""
Write-Host "Enabling TimescaleDB extension..."
Invoke-Expression $enableExtensionCmd

# Set default privileges
$setDefaultPrivilegesCmd = "psql -h $PGHOST -p $PGPORT -U $PGUSER -d trading_db -c ""ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO trading_user; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO trading_user;"""
Write-Host "Setting default privileges..."
Invoke-Expression $setDefaultPrivilegesCmd

# Make trading_user a superuser (to create extensions)
$makeSuperuserCmd = "psql -h $PGHOST -p $PGPORT -U $PGUSER -c ""ALTER USER trading_user WITH SUPERUSER;"""
Write-Host "Making trading_user a superuser..."
Invoke-Expression $makeSuperuserCmd

Write-Host "Database setup completed!"
$env:PGPASSWORD = ""  # Clear password from environment