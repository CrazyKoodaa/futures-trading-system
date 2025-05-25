@echo off
echo Creating PostgreSQL admin user for futures trading system...

set /p PGPASSWORD=Enter postgres user password: 

echo Creating trading_admin user with full database creation rights...
psql -h localhost -p 5432 -U postgres -f create_admin_user.sql

echo.
echo Admin user setup completed!
echo Username: trading_admin
echo Password: myAdmin4Tr4ding42!
echo This user has full rights to create databases and tables

set PGPASSWORD=

pause