@echo off
echo Setting up PostgreSQL database for futures trading system...

set /p PGPASSWORD=Enter postgres user password: 

echo Creating database user and setting up permissions...
psql -h localhost -p 5432 -U postgres -f create_db_user.sql

echo Database setup completed!
set PGPASSWORD=

pause