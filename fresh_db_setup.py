#!/usr/bin/env python3
"""
Fresh database setup script that drops everything and recreates it cleanly.
No retention policies - all data will be saved permanently.
"""

import asyncio
import os
import sys
import logging
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def drop_and_recreate_database():
    """Drop the entire database and recreate it fresh"""
    
    # Use admin credentials
    user = os.getenv('POSTGRES_ADMIN_USER', 'trading_admin')
    password = os.getenv('POSTGRES_ADMIN_PASSWORD', 'myAdmin4Tr4ding42!')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    database = os.getenv('POSTGRES_DB', 'trading_db')
    
    logger.info(f"🗑️  Dropping and recreating database: {database}")
    
    try:
        # First connect to postgres database to drop trading_db
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to postgres db first
        )
        
        logger.info("✅ Connected to postgres database")
        
        # Terminate all connections to trading_db
        await conn.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{database}' AND pid <> pg_backend_pid();
        """)
        
        # Drop the database
        await conn.execute(f"DROP DATABASE IF EXISTS {database};")
        logger.info(f"🗑️  Dropped database: {database}")
        
        # Create the database
        await conn.execute(f"CREATE DATABASE {database} WITH OWNER = {user};")
        logger.info(f"🆕 Created database: {database}")
        
        await conn.close()
        
        # Now connect to the new database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        logger.info(f"✅ Connected to new database: {database}")
        
        # Create TimescaleDB extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        logger.info("✅ TimescaleDB extension created")
        
        # Create additional extensions
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
            logger.info("✅ pg_stat_statements extension created")
        except Exception as e:
            logger.warning(f"Could not create pg_stat_statements: {e}")
        
        # Create all tables
        logger.info("🔧 Creating tables...")
        
        # Market data seconds table
        await conn.execute("""
            CREATE TABLE market_data_seconds (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                contract VARCHAR(10) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                exchange_code VARCHAR(10),
                open DECIMAL(12,4) NOT NULL,
                high DECIMAL(12,4) NOT NULL,
                low DECIMAL(12,4) NOT NULL,
                close DECIMAL(12,4) NOT NULL,
                volume INTEGER DEFAULT 0,
                tick_count INTEGER DEFAULT 0,
                vwap DECIMAL(12,4),
                bid DECIMAL(12,4),
                ask DECIMAL(12,4),
                spread DECIMAL(12,4),
                data_quality_score DECIMAL(3,2) DEFAULT 1.0,
                is_regular_hours BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (timestamp, symbol, contract, exchange)
            );
        """)
        logger.info("✅ Created market_data_seconds table")
        
        # Raw tick data table
        await conn.execute("""
            CREATE TABLE raw_tick_data (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                contract VARCHAR(10) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                price DECIMAL(12,4) NOT NULL,
                size INTEGER DEFAULT 0,
                tick_type VARCHAR(10) NOT NULL,
                exchange_timestamp TIMESTAMPTZ,
                sequence_number BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (timestamp, symbol, contract, exchange, sequence_number)
            );
        """)
        logger.info("✅ Created raw_tick_data table")
        
        # Market data minutes table
        await conn.execute("""
            CREATE TABLE market_data_minutes (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                contract VARCHAR(10) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                open DECIMAL(12,4) NOT NULL,
                high DECIMAL(12,4) NOT NULL,
                low DECIMAL(12,4) NOT NULL,
                close DECIMAL(12,4) NOT NULL,
                volume INTEGER DEFAULT 0,
                tick_count INTEGER DEFAULT 0,
                vwap DECIMAL(12,4),
                avg_spread DECIMAL(12,4),
                max_spread DECIMAL(12,4),
                trade_count INTEGER DEFAULT 0,
                PRIMARY KEY (timestamp, symbol, contract, exchange)
            );
        """)
        logger.info("✅ Created market_data_minutes table")
        
        # Features table
        await conn.execute("""
            CREATE TABLE features (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                contract VARCHAR(10) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                timeframe VARCHAR(5) NOT NULL,
                sma_5 DECIMAL(12,4),
                sma_10 DECIMAL(12,4),
                sma_20 DECIMAL(12,4),
                sma_50 DECIMAL(12,4),
                ema_12 DECIMAL(12,4),
                ema_26 DECIMAL(12,4),
                macd DECIMAL(12,6),
                macd_signal DECIMAL(12,6),
                macd_histogram DECIMAL(12,6),
                rsi DECIMAL(5,2),
                stoch_k DECIMAL(5,2),
                stoch_d DECIMAL(5,2),
                williams_r DECIMAL(5,2),
                roc DECIMAL(8,4),
                bb_upper DECIMAL(12,4),
                bb_middle DECIMAL(12,4),
                bb_lower DECIMAL(12,4),
                bb_width DECIMAL(8,4),
                atr DECIMAL(8,4),
                volume_sma DECIMAL(12,2),
                volume_ratio DECIMAL(6,3),
                obv BIGINT,
                relative_volume DECIMAL(6,3),
                exchange_rank INTEGER,
                PRIMARY KEY (timestamp, symbol, contract, exchange, timeframe)
            );
        """)
        logger.info("✅ Created features table")
        
        # Predictions table
        await conn.execute("""
            CREATE TABLE predictions (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                contract VARCHAR(10) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                model_version VARCHAR(50) NOT NULL,
                model_type VARCHAR(20) NOT NULL,
                direction_prediction INTEGER,
                confidence_score DECIMAL(5,2),
                pip_movement_prediction DECIMAL(8,4),
                long_probability DECIMAL(5,4),
                short_probability DECIMAL(5,4),
                prediction_horizon_minutes INTEGER,
                exchange_adjustment_factor DECIMAL(6,4) DEFAULT 1.0,
                features_used TEXT[],
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (timestamp, symbol, contract, exchange, model_version)
            );
        """)
        logger.info("✅ Created predictions table")
        
        # Trades table - Fixed structure that works with TimescaleDB
        await conn.execute("""
            CREATE SEQUENCE trades_trade_id_seq;
        """)
        
        await conn.execute("""
            CREATE TABLE trades (
                timestamp TIMESTAMPTZ NOT NULL,
                trade_id BIGINT NOT NULL DEFAULT nextval('trades_trade_id_seq'),
                symbol VARCHAR(10) NOT NULL,
                contract VARCHAR(10) NOT NULL,
                exchange VARCHAR(10) NOT NULL,
                side VARCHAR(10) NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price DECIMAL(12,4) NOT NULL,
                exit_timestamp TIMESTAMPTZ,
                exit_price DECIMAL(12,4),
                pnl DECIMAL(12,2),
                pnl_percent DECIMAL(8,4),
                commission DECIMAL(8,2) DEFAULT 0,
                confidence_at_entry DECIMAL(5,2),
                model_version VARCHAR(50),
                route_exchange VARCHAR(10),
                execution_venue VARCHAR(20),
                trade_type VARCHAR(20) DEFAULT 'ALGO',
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        # Add primary key constraint after table creation
        await conn.execute("""
            ALTER TABLE trades ADD CONSTRAINT trades_pkey PRIMARY KEY (timestamp, trade_id);
        """)
        logger.info("✅ Created trades table with sequence")
        
        # Create hypertables
        logger.info("⏰ Converting tables to hypertables...")
        
        hypertables = [
            {'table': 'market_data_seconds', 'interval': "INTERVAL '1 minute'"},
            {'table': 'raw_tick_data', 'interval': "INTERVAL '10 seconds'"},
            {'table': 'market_data_minutes', 'interval': "INTERVAL '1 hour'"},
            {'table': 'features', 'interval': "INTERVAL '1 day'"},
            {'table': 'predictions', 'interval': "INTERVAL '1 day'"},
            {'table': 'trades', 'interval': "INTERVAL '1 day'"}
        ]
        
        for ht in hypertables:
            try:
                await conn.execute(f"""
                    SELECT create_hypertable('{ht['table']}', 'timestamp',
                    chunk_time_interval => {ht['interval']});
                """)
                logger.info(f"✅ Created hypertable: {ht['table']}")
            except Exception as e:
                logger.warning(f"Could not create hypertable {ht['table']}: {e}")
        
        # Create indexes for better performance
        logger.info("📊 Creating indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_symbol_time ON market_data_seconds (symbol, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_contract_time ON market_data_seconds (contract, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_exchange_time ON market_data_seconds (exchange, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_raw_tick_data_contract_time ON raw_tick_data (contract, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_raw_tick_data_type ON raw_tick_data (tick_type, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_features_symbol_timeframe_time ON features (symbol, timeframe, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_predictions_symbol_model_time ON predictions (symbol, model_version, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_trades_exchange ON trades (exchange, timestamp DESC);"
        ]
        
        for idx_sql in indexes:
            try:
                await conn.execute(idx_sql)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
        
        logger.info("✅ Created indexes")
        
        # Grant permissions to trading_user
        logger.info("🔐 Setting up permissions...")
        
        await conn.execute("""
            GRANT CONNECT ON DATABASE trading_db TO trading_user;
            GRANT USAGE ON SCHEMA public TO trading_user;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
            GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO trading_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO trading_user;
        """)
        logger.info("✅ Permissions set up")
        
        # Test data insertion
        logger.info("🧪 Testing data insertion...")
        
        await conn.execute("""
            INSERT INTO market_data_seconds (
                timestamp, symbol, contract, exchange, exchange_code,
                open, high, low, close, volume, tick_count, vwap,
                bid, ask, spread, data_quality_score, is_regular_hours
            ) VALUES (
                NOW(), 'NQ', 'NQZ24', 'CME', 'XCME',
                17245.50, 17246.00, 17245.25, 17245.75, 150, 12, 17245.68,
                17245.50, 17245.75, 0.25, 1.0, TRUE
            );
        """)
        
        await conn.execute("""
            INSERT INTO trades (
                timestamp, symbol, contract, exchange, side, quantity, entry_price
            ) VALUES (
                NOW(), 'NQ', 'NQZ24', 'CME', 'BUY', 1, 17245.50
            );
        """)
        
        logger.info("✅ Test data insertion successful")
        
        # Verify setup
        logger.info("🔍 Verifying database setup...")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        logger.info(f"📋 Found {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table['table_name']}")
        
        # Check hypertables
        hypertables = await conn.fetch("""
            SELECT hypertable_name, num_chunks
            FROM timescaledb_information.hypertables
            ORDER BY hypertable_name;
        """)
        
        logger.info(f"⏰ Found {len(hypertables)} hypertables:")
        for ht in hypertables:
            logger.info(f"  - {ht['hypertable_name']} ({ht['num_chunks']} chunks)")
        
        # Check data
        test_data_count = await conn.fetchval("SELECT COUNT(*) FROM market_data_seconds;")
        test_trades_count = await conn.fetchval("SELECT COUNT(*) FROM trades;")
        
        logger.info(f"📊 Test data: {test_data_count} market_data_seconds, {test_trades_count} trades")
        
        await conn.close()
        
        logger.info("🎉 Database setup completed successfully!")
        logger.info("💾 NO RETENTION POLICIES - All data will be kept permanently!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False

async def main():
    """Main function"""
    
    logger.info("🚀 Starting fresh TimescaleDB database setup...")
    logger.info("⚠️  This will DROP the existing database and recreate it!")
    
    # Ask for confirmation
    try:
        confirmation = input("Are you sure you want to drop and recreate the database? (type 'yes' to continue): ")
        if confirmation.lower() != 'yes':
            logger.info("❌ Operation cancelled by user")
            return False
    except KeyboardInterrupt:
        logger.info("❌ Operation cancelled by user")
        return False
    
    success = await drop_and_recreate_database()
    
    if success:
        logger.info("✅ Fresh database setup completed successfully!")
        logger.info("\n📝 Next steps:")
        logger.info("1. Your database is now clean and ready")
        logger.info("2. All data will be kept permanently (no retention policies)")
        logger.info("3. Test with: python admin_rithmic.py")
        logger.info("4. Start collecting data with your tick collection system")
        return True
    else:
        logger.error("❌ Fresh database setup failed!")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ Fresh database setup completed successfully!")
        else:
            print("\n❌ Fresh database setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Database setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)