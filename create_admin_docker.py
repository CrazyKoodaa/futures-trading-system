# create_admin_docker.py
import asyncio
import asyncpg
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_admin_and_database():
    """Create the trading_admin user and trading_db database in Docker container"""
    # Connection parameters for postgres user in Docker
    postgres_password = "mysecretpassword"  # Default password from Docker container
    
    try:
        # Connect to the default postgres database as postgres user
        logger.info("Connecting to PostgreSQL in Docker container as postgres user...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=postgres_password,
            database='postgres'
        )
        
        # Create trading_admin user with full privileges
        logger.info("Creating trading_admin user with full privileges...")
        await conn.execute("""
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
                ELSE
                    ALTER USER trading_admin WITH 
                        PASSWORD 'myAdmin4Tr4ding42!'
                        SUPERUSER
                        CREATEDB
                        CREATEROLE
                        INHERIT
                        LOGIN
                        REPLICATION
                        BYPASSRLS;
                END IF;
            END
            $$;
        """)
        logger.info("User trading_admin created/updated successfully")
        
        # Check if trading_db exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'trading_db'"
        )
        
        if not db_exists:
            logger.info("Creating trading_db database...")
            await conn.execute(
                "CREATE DATABASE trading_db WITH OWNER = trading_admin"
            )
            logger.info("Database trading_db created successfully")
        else:
            logger.info("Database trading_db already exists")
            # Change owner to trading_admin
            await conn.execute(
                "ALTER DATABASE trading_db OWNER TO trading_admin"
            )
            logger.info("Changed owner of trading_db to trading_admin")
        
        # Grant privileges
        logger.info("Granting privileges to trading_admin...")
        await conn.execute(
            "GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_admin"
        )
        
        await conn.close()
        
        # Connect to trading_db to set up schema and extensions
        logger.info("Connecting to trading_db to set up schema and extensions...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='trading_admin',
            password='myAdmin4Tr4ding42!',
            database='trading_db'
        )
        
        # Create TimescaleDB extension
        logger.info("Creating TimescaleDB extension...")
        try:
            await conn.execute(
                "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"
            )
            logger.info("TimescaleDB extension created successfully")
        except Exception as e:
            logger.error(f"Failed to create TimescaleDB extension: {e}")
            logger.warning("Make sure TimescaleDB is installed in your Docker container")
        
        # Create regular trading_user with limited privileges
        logger.info("Creating regular trading_user...")
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_user') THEN
                    CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!';
                ELSE
                    ALTER USER trading_user WITH PASSWORD 'myData4Tr4ding42!';
                END IF;
            END
            $$;
        """)
        
        # Grant necessary privileges to trading_user
        logger.info("Granting necessary privileges to trading_user...")
        await conn.execute("""
            GRANT CONNECT ON DATABASE trading_db TO trading_user;
            GRANT USAGE ON SCHEMA public TO trading_user;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
            GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO trading_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO trading_user;
        """)
        
        await conn.close()
        
        logger.info("Database setup completed successfully!")
        logger.info("Admin user: trading_admin / myAdmin4Tr4ding42!")
        logger.info("Regular user: trading_user / myData4Tr4ding42!")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(create_admin_and_database())
    if not success:
        sys.exit(1)