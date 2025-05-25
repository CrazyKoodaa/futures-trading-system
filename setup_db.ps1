# PowerShell script to create PostgreSQL user and database using the SQL file

# Set PostgreSQL connection parameters
$PGHOST = "localhost"
$PGPORT = "5432"
$PGUSER = "postgres"
$PGPASSWORD = Read-Host -Prompt "Enter postgres user password" -AsSecureString
$PGPASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($PGPASSWORD))

# Execute the SQL file
$env:PGPASSWORD = $PGPASSWORD_PLAIN
Write-Host "Creating database user and setting up permissions..."
psql -h $PGHOST -p $PGPORT -U $PGUSER -f "create_db_user.sql"

Write-Host "Database setup completed!"
$env:PGPASSWORD = ""  # Clear password from environment