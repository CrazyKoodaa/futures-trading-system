-- create_admin_user.sql
-- Script to create a trading_admin user with full database creation rights

-- Create the trading_admin user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_admin') THEN
        CREATE USER trading_admin WITH 
            PASSWORD 'myAdmin4Tr4ding42!'
            SUPERUSER
            CREATEDB
            CREATEROLE
            INHERIT
            LOGIN
            REPLICATION
            BYPASSRLS;
        
        RAISE NOTICE 'User trading_admin created successfully with full admin rights';
    ELSE
        -- Update the existing user with the required permissions
        ALTER USER trading_admin WITH 
            PASSWORD 'myAdmin4Tr4ding42!'
            SUPERUSER
            CREATEDB
            CREATEROLE
            INHERIT
            LOGIN
            REPLICATION
            BYPASSRLS;
            
        RAISE NOTICE 'User trading_admin already exists, permissions updated';
    END IF;
END
$$;

-- Grant additional privileges to the trading_admin user
GRANT ALL PRIVILEGES ON DATABASE postgres TO trading_admin;

-- If trading_db exists, grant privileges on it too
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_database WHERE datname = 'trading_db') THEN
        GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_admin;
        RAISE NOTICE 'Granted all privileges on trading_db to trading_admin';
    END IF;
END
$$;

-- Output confirmation
DO $$
BEGIN
    RAISE NOTICE 'trading_admin user setup completed successfully';
    RAISE NOTICE 'This user has full administrative rights to create databases and tables';
    RAISE NOTICE 'Username: trading_admin';
    RAISE NOTICE 'Password: myAdmin4Tr4ding42!';
END
$$;