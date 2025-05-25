# PowerShell script to create PostgreSQL admin user

# Set PostgreSQL connection parameters
$PGHOST = "localhost"
$PGPORT = "5432"
$PGUSER = "postgres"
$PGPASSWORD = Read-Host -Prompt "Enter postgres user password" -AsSecureString
$PGPASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($PGPASSWORD))

# Execute the SQL file
$env:PGPASSWORD = $PGPASSWORD_PLAIN
Write-Host "Creating trading_admin user with full database creation rights..."
psql -h $PGHOST -p $PGPORT -U $PGUSER -f "create_admin_user.sql"

Write-Host "`nAdmin user setup completed!"
Write-Host "Username: trading_admin"
Write-Host "Password: myAdmin4Tr4ding42!"
Write-Host "This user has full rights to create databases and tables"

# Clear password from environment
$env:PGPASSWORD = ""