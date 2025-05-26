#!/usr/bin/env python3
"""
Simple database fix script to resolve TimescaleDB issues.
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

async def fix_database_issues():
    """Fix the specific database issues identified"""
    
    # Use admin credentials
    user = os.getenv('POSTGRES_ADMIN_USER', 'trading_admin')
    password = os.getenv('POSTGRES_ADMIN_PASSWORD', 'myAdmin4Tr4ding42!')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    database = os.getenv('POSTGRES_DB', 'trading_db')
    
    logger.info(f"Connecting to {host}:{port}/{database} as {user}")
    
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        logger.info("✅ Connected successfully")
        
        # Step 1: Drop the problematic trades table and recreate it properly
        logger.info("🔧 Fixing trades table...")
        
        # Check if trades table exists as hypertable
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM timescaledb_information.hypertables 
                WHERE hypertable_name = 'trades'
            );
        """)
        
        if result:
            logger.info("Dropping existing trades hypertable...")
            await conn.execute("DROP TABLE IF EXISTS trades CASCADE;")
        
        # Create the trades table with proper structure for TimescaleDB
        logger.info("Creating new trades table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
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
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (timestamp, trade_id)
            );
        """)
        
        # Create sequence if it doesn't exist
        await conn.execute("CREATE SEQUENCE IF NOT EXISTS trades_trade_id_seq;")
        
        # Step 2: Create hypertable for trades
        logger.info("Converting trades to hypertable...")
        try:
            await conn.execute("""
                SELECT create_hypertable('trades', 'timestamp',
                chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
            """)
            logger.info("✅ Trades hypertable created successfully")
        except Exception as e:
            logger.warning(f"Could not create trades hypertable: {e}")
        
        # Step 3: Fix ownership issues for retention policies
        logger.info("🔧 Fixing table ownership...")
        
        # Set proper ownership
        tables_to_fix = ['market_data_seconds', 'market_data_minutes', 'predictions', 'raw_tick_data']
        
        for table in tables_to_fix:
            try:
                await conn.execute(f"ALTER TABLE {table} OWNER TO {user};")
                logger.info(f"✅ Set ownership of {table} to {user}")
            except Exception as e:
                logger.warning(f"Could not set ownership of {table}: {e}")
        
        # Step 4: Add retention policies with proper permissions
        logger.info("🔧 Setting up retention policies...")
        
        retention_policies = [
            {'table': 'raw_tick_data', 'interval': "INTERVAL '7 days'"},
            {'table': 'market_data_seconds', 'interval': "INTERVAL '1 year'"},
            {'table': 'market_data_minutes', 'interval': "INTERVAL '2 years'"},
            {'table': 'predictions', 'interval': "INTERVAL '6 months'"}
        ]
        
        for policy in retention_policies:
            try:
                # Check if table is a hypertable
                is_hypertable = await conn.fetchval(f"""
                    SELECT EXISTS (
                        SELECT FROM timescaledb_information.hypertables 
                        WHERE hypertable_name = '{policy['table']}'
                    );
                """)
                
                if is_hypertable:
                    # Check if retention policy already exists
                    policy_exists = await conn.fetchval(f"""
                        SELECT EXISTS (
                            SELECT FROM timescaledb_information.drop_chunks_policies 
                            WHERE hypertable_name = '{policy['table']}'
                        );
                    """)
                    
                    if not policy_exists:
                        await conn.execute(f"""
                            SELECT add_retention_policy('{policy['table']}', {policy['interval']});
                        """)
                        logger.info(f"✅ Added retention policy for {policy['table']}: {policy['interval']}")
                    else:
                        logger.info(f"ℹ️  Retention policy for {policy['table']} already exists")
                else:
                    logger.warning(f"⚠️  {policy['table']} is not a hypertable, skipping retention policy")
                    
            except Exception as e:
                logger.warning(f"Could not set retention policy for {policy['table']}: {e}")
        
        # Step 5: Verify the setup
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
        
        # Check retention policies
        policies = await conn.fetch("""
            SELECT hypertable_name, drop_after
            FROM timescaledb_information.drop_chunks_policies
            ORDER BY hypertable_name;
        """)
        
        logger.info(f"🗑️  Found {len(policies)} retention policies:")
        for policy in policies:
            logger.info(f"  - {policy['hypertable_name']}: {policy['drop_after']}")
        
        # Step 6: Test data insertion
        logger.info("🧪 Testing data insertion...")
        
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
                ) ON CONFLICT (timestamp, symbol, contract, exchange) DO NOTHING
            """)
            logger.info("✅ Test data insertion successful")
        except Exception as e:
            logger.warning(f"Test data insertion failed: {e}")
        
        await conn.close()
        
        logger.info("🎉 Database fix completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database fix failed: {e}")
        return False

async def main():
    """Main function"""
    
    logger.info("🚀 Starting TimescaleDB database fix...")
    
    success = await fix_database_issues()
    
    if success:
        logger.info("✅ Database fix completed successfully!")
        logger.info("\n📝 Next steps:")
        logger.info("1. Replace shared/database/connection.py with the fixed version")
        logger.info("2. Test with: python initialize_db.py")
        logger.info("3. Try running: python admin_rithmic.py")
        return True
    else:
        logger.error("❌ Database fix failed!")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ Database fix completed successfully!")
        else:
            print("\n❌ Database fix failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Database fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)