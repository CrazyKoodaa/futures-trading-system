# setup_database_admin.py
import asyncio
import os
import sys
import logging
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def setup_database():
    """Set up the database using the admin user"""
    try:
        # Connect as admin user
        logger.info("Connecting to database as admin user...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='trading_admin',
            password='myAdmin4Tr4ding42!',
            database='trading_db'
        )
        
        # Create extensions
        logger.info("Creating required extensions...")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
            logger.info("pg_stat_statements extension created successfully")
        except Exception as e:
            logger.warning(f"Could not create pg_stat_statements extension: {e}")
            logger.warning("This is not critical, continuing setup...")
        
        # Make sure TimescaleDB extension is created
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            logger.info("TimescaleDB extension created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create TimescaleDB extension: {e}")
            logger.error("This is critical for the application to function properly")
            return False
        
        # Create hypertables and other database objects
        logger.info("Setting up database schema...")
        
        # Create market data tables if they don't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data_seconds (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                contract TEXT,
                exchange TEXT NOT NULL,
                exchange_code TEXT,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume DOUBLE PRECISION,
                tick_count INTEGER,
                vwap DOUBLE PRECISION,
                bid DOUBLE PRECISION,
                ask DOUBLE PRECISION,
                spread DOUBLE PRECISION,
                data_quality_score DOUBLE PRECISION,
                is_regular_hours BOOLEAN,
                PRIMARY KEY (timestamp, symbol, exchange)
            )
        """)
        
        # Create minute data table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data_minutes (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                contract TEXT,
                exchange TEXT NOT NULL,
                exchange_code TEXT,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume DOUBLE PRECISION,
                tick_count INTEGER,
                vwap DOUBLE PRECISION,
                bid DOUBLE PRECISION,
                ask DOUBLE PRECISION,
                spread DOUBLE PRECISION,
                data_quality_score DOUBLE PRECISION,
                is_regular_hours BOOLEAN,
                PRIMARY KEY (timestamp, symbol, exchange)
            )
        """)
        
        # Convert market_data_seconds to a hypertable
        try:
            await conn.execute("""
                SELECT create_hypertable('market_data_seconds', 'timestamp', 
                                        if_not_exists => TRUE,
                                        create_default_indexes => TRUE,
                                        chunk_time_interval => INTERVAL '1 day')
            """)
            logger.info("market_data_seconds hypertable created/verified")
            
            # Create indexes for efficient querying
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_seconds_symbol 
                ON market_data_seconds (symbol, exchange, timestamp DESC)
            """)
        except Exception as e:
            logger.error(f"Failed to create market_data_seconds hypertable: {e}")
            return False
        
        # Convert market_data_minutes to a hypertable
        try:
            await conn.execute("""
                SELECT create_hypertable('market_data_minutes', 'timestamp', 
                                        if_not_exists => TRUE,
                                        create_default_indexes => TRUE,
                                        chunk_time_interval => INTERVAL '1 week')
            """)
            logger.info("market_data_minutes hypertable created/verified")
            
            # Create indexes for efficient querying
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_minutes_symbol 
                ON market_data_minutes (symbol, exchange, timestamp DESC)
            """)
        except Exception as e:
            logger.error(f"Failed to create market_data_minutes hypertable: {e}")
            return False
        
        # Set up retention policies
        try:
            await conn.execute("""
                SELECT add_retention_policy('market_data_seconds', 
                                          INTERVAL '7 days', 
                                          if_not_exists => TRUE)
            """)
            logger.info("Retention policy for market_data_seconds set to 7 days")
            
            await conn.execute("""
                SELECT add_retention_policy('market_data_minutes', 
                                          INTERVAL '90 days', 
                                          if_not_exists => TRUE)
            """)
            logger.info("Retention policy for market_data_minutes set to 90 days")
        except Exception as e:
            logger.warning(f"Failed to set retention policies: {e}")
            logger.warning("This is not critical, continuing setup...")
        
        # Insert test data
        logger.info("Inserting test data...")
        try:
            await conn.execute("""
                INSERT INTO market_data_seconds (
                    timestamp, symbol, contract, exchange, exchange_code,
                    open, high, low, close, volume, tick_count, vwap,
                    bid, ask, spread, data_quality_score, is_regular_hours
                ) VALUES (
                    NOW(), 'NQ', 'NQZ24', 'CME', 'XCME',
                    17245.50, 17246.00, 17245.25, 17245.75, 150, 12, 17245.68,
                    17245.50, 17245.75, 0.25, 1.0, TRUE
                ) ON CONFLICT (timestamp, symbol, exchange) DO NOTHING
            """)
            logger.info("Test data inserted successfully")
        except Exception as e:
            logger.warning(f"Failed to insert test data: {e}")
            logger.warning("This is not critical, continuing setup...")
        
        # Grant privileges to trading_user
        logger.info("Granting privileges to trading_user...")
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
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(setup_database())
    if success:
        print("[SUCCESS] Database ready for tick collection!")
    else:
        print("[ERROR] Database setup failed")
        sys.exit(1)