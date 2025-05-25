# create_db.py
import asyncio
import asyncpg
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_database():
    """Create the trading database and user if they don't exist"""
    # Connection parameters for postgres user
    postgres_password = input("Enter postgres user password: ")
    
    try:
        # Connect to the default postgres database as postgres user
        logger.info("Connecting to PostgreSQL as postgres user...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=postgres_password,
            database='postgres'
        )
        
        # Check if trading_user exists
        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = 'trading_user'"
        )
        
        if not user_exists:
            logger.info("Creating trading_user...")
            await conn.execute(
                "CREATE USER trading_user WITH PASSWORD 'myData4Tr4ding42!'"
            )
            logger.info("User trading_user created successfully")
        else:
            logger.info("User trading_user already exists")
            
            # Update password if needed
            logger.info("Updating trading_user password...")
            await conn.execute(
                "ALTER USER trading_user WITH PASSWORD 'myData4Tr4ding42!'"
            )
        
        # Check if trading_db exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'trading_db'"
        )
        
        if not db_exists:
            logger.info("Creating trading_db database...")
            await conn.execute(
                "CREATE DATABASE trading_db WITH OWNER = trading_user"
            )
            logger.info("Database trading_db created successfully")
        else:
            logger.info("Database trading_db already exists")
        
        # Grant privileges
        logger.info("Granting privileges to trading_user...")
        await conn.execute(
            "GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user"
        )
        
        # Make trading_user a superuser (to create extensions)
        logger.info("Making trading_user a superuser...")
        await conn.execute(
            "ALTER USER trading_user WITH SUPERUSER"
        )
        
        await conn.close()
        
        # Connect to trading_db to set up schema privileges
        logger.info("Connecting to trading_db to set up schema privileges...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=postgres_password,
            database='trading_db'
        )
        
        # Grant schema privileges
        logger.info("Granting schema privileges...")
        await conn.execute(
            "GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user"
        )
        
        # Set default privileges
        logger.info("Setting default privileges...")
        await conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO trading_user"
        )
        await conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO trading_user"
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
            logger.warning("Make sure TimescaleDB is installed on your PostgreSQL server")
        
        await conn.close()
        
        logger.info("Database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(create_database())
    if not success:
        sys.exit(1)