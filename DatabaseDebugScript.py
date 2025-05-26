import asyncio
import logging
from datetime import datetime
from shared.database.connection import get_async_session, TimescaleDBHelper, get_database_manager
from sqlalchemy import text

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_database_insertion():
    """Debug database insertion issues"""
    print("🔍 Debugging Database Insertion Issues")
    print("=" * 60)
    
    try:
        # Test 1: Basic connection
        print("1. Testing basic database connection...")
        db_manager = get_database_manager()
        connection_ok = await db_manager.test_connection()
        
        if not connection_ok:
            print("❌ Database connection failed!")
            return False
        print("✅ Database connection successful")
        
        # Test 2: Check table existence
        print("\n2. Checking table structure...")
        async with get_async_session() as session:
            # Check if tables exist
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('market_data_seconds', 'market_data_minutes')
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            
            if not tables:
                print("❌ Required tables not found!")
                print("💡 Run: python initialize_db.py")
                return False
            
            print(f"✅ Found tables: {', '.join([t[0] for t in tables])}")
            
            # Check table structure
            for table_name in ['market_data_seconds', 'market_data_minutes']:
                result = await session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                print(f"\n📋 Table '{table_name}' columns ({len(columns)}):")
                for col in columns[:5]:  # Show first 5 columns
                    print(f"   - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
                if len(columns) > 5:
                    print(f"   ... and {len(columns) - 5} more columns")
        
        # Test 3: Check hypertable status
        print("\n3. Checking hypertable status...")
        async with get_async_session() as session:
            result = await session.execute(text("""
                SELECT hypertable_name, num_chunks, num_dimensions
                FROM timescaledb_information.hypertables
                WHERE hypertable_name IN ('market_data_seconds', 'market_data_minutes')
                ORDER BY hypertable_name;
            """))
            hypertables = result.fetchall()
            
            if not hypertables:
                print("⚠️  No hypertables found - tables are regular PostgreSQL tables")
                print("💡 This may cause performance issues but shouldn't prevent insertion")
            else:
                for ht in hypertables:
                    print(f"✅ Hypertable: {ht[0]} ({ht[1]} chunks, {ht[2]} dimensions)")
        
        # Test 4: Test simple insertion
        print("\n4. Testing simple data insertion...")
        async with get_async_session() as session:
            helper = TimescaleDBHelper(session)
            
            # Create test record
            test_record = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'contract': 'TESTX24',
                'exchange': 'TEST',
                'exchange_code': 'XTEST',
                'open': 100.00,
                'high': 101.00,
                'low': 99.00,
                'close': 100.50,
                'volume': 1000,
                'tick_count': 10,
                'vwap': 100.25,
                'bid': 100.25,
                'ask': 100.75,
                'spread': 0.50,
                'data_quality_score': 1.0,
                'is_regular_hours': True
            }
            
            # Test insertion into market_data_seconds
            try:
                await helper.bulk_insert_market_data([test_record], 'market_data_seconds')
                print("✅ Test insertion to market_data_seconds successful")
                
                # Verify the record was inserted
                result = await session.execute(text("""
                    SELECT COUNT(*) FROM market_data_seconds 
                    WHERE symbol = 'TEST' AND contract = 'TESTX24'
                """))
                count = result.scalar()
                print(f"✅ Verified: {count} test record(s) found")
                
                # Clean up test data
                await session.execute(text("""
                    DELETE FROM market_data_seconds 
                    WHERE symbol = 'TEST' AND contract = 'TESTX24'
                """))
                await session.commit()
                print("✅ Test data cleaned up")
                
            except Exception as e:
                print(f"❌ Test insertion failed: {e}")
                logger.exception("Test insertion failed")
                return False
        
        # Test 5: Check existing data
        print("\n5. Checking existing data...")
        async with get_async_session() as session:
            # Count total records
            result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
            second_count = result.scalar()
            
            result = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
            minute_count = result.scalar()
            
            print(f"📊 Current data counts:")
            print(f"   - market_data_seconds: {second_count:,} records")
            print(f"   - market_data_minutes: {minute_count:,} records")
            
            # Show recent data if any exists
            if second_count > 0:
                result = await session.execute(text("""
                    SELECT symbol, contract, exchange, timestamp, close, volume
                    FROM market_data_seconds
                    ORDER BY timestamp DESC
                    LIMIT 5
                """))
                recent_data = result.fetchall()
                print(f"\n📈 Recent market_data_seconds records:")
                for row in recent_data:
                    print(f"   {row[0]} {row[1]} @ {row[3]}: ${row[4]} (Vol: {row[5]})")
            
            # Check for common issues
            result = await session.execute(text("""
                SELECT symbol, COUNT(*) as count
                FROM market_data_seconds
                GROUP BY symbol
                ORDER BY count DESC
                LIMIT 10
            """))
            symbol_counts = result.fetchall()
            
            if symbol_counts:
                print(f"\n📊 Data by symbol:")
                for symbol, count in symbol_counts:
                    print(f"   {symbol}: {count:,} records")
        
        # Test 6: Check constraints and indexes
        print("\n6. Checking constraints and indexes...")
        async with get_async_session() as session:
            # Check primary key constraints
            result = await session.execute(text("""
                SELECT tc.table_name, string_agg(kcu.column_name, ', ') as key_columns
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name IN ('market_data_seconds', 'market_data_minutes')
                GROUP BY tc.table_name;
            """))
            constraints = result.fetchall()
            
            for table, columns in constraints:
                print(f"🔑 Primary key for {table}: ({columns})")
            
            # Check indexes
            result = await session.execute(text("""
                SELECT tablename, indexname, indexdef
                FROM pg_indexes
                WHERE tablename IN ('market_data_seconds', 'market_data_minutes')
                AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname;
            """))
            indexes = result.fetchall()
            
            if indexes:
                print(f"\n📇 Custom indexes found: {len(indexes)}")
                for table, idx_name, idx_def in indexes[:5]:  # Show first 5
                    print(f"   {table}: {idx_name}")
            else:
                print("⚠️  No custom indexes found - may impact query performance")
        
        # Test 7: Check permissions
        print("\n7. Checking user permissions...")
        async with get_async_session() as session:
            # Check current user
            result = await session.execute(text("SELECT current_user, current_database()"))
            user, db = result.fetchone()
            print(f"👤 Current user: {user} in database: {db}")
            
            # Check table permissions
            result = await session.execute(text("""
                SELECT table_name, privilege_type
                FROM information_schema.role_table_grants
                WHERE grantee = current_user
                AND table_name IN ('market_data_seconds', 'market_data_minutes')
                ORDER BY table_name, privilege_type;
            """))
            permissions = result.fetchall()
            
            if permissions:
                print("✅ User permissions:")
                current_table = None
                for table, privilege in permissions:
                    if table != current_table:
                        print(f"   {table}:", end="")
                        current_table = table
                    print(f" {privilege}", end="")
                print()  # New line after last table
            else:
                print("⚠️  No explicit table permissions found")
        
        print("\n" + "=" * 60)
        print("✅ Database debugging completed successfully!")
        print("\n💡 Recommendations:")
        
        if second_count == 0 and minute_count == 0:
            print("   - No data found. Check that data download completed without errors")
            print("   - Review logs in rithmic_admin.log for detailed error messages")
            print("   - Ensure Rithmic API returned actual data (not empty responses)")
        
        if not hypertables:
            print("   - Consider running fresh_db_setup.py to create proper hypertables")
        
        print("   - Monitor logs during data download for specific error messages")
        print("   - Check Rithmic API responses are not empty before database insertion")
        
        return True
        
    except Exception as e:
        print(f"❌ Database debugging failed: {e}")
        logger.exception("Database debugging failed")
        return False

async def test_rithmic_data_format():
    """Test what format Rithmic actually returns"""
    print("\n🔍 Testing Rithmic Data Format")
    print("=" * 40)
    
    try:
        from config.chicago_gateway_config import get_chicago_gateway_config
        from async_rithmic import RithmicClient, TimeBarType, Gateway
        from datetime import datetime, timedelta
        
        config = get_chicago_gateway_config()
        gateway = Gateway.CHICAGO if config['rithmic']['gateway'] == 'Chicago' else Gateway.TEST
        
        client = RithmicClient(
            user=config['rithmic']['user'],
            password=config['rithmic']['password'],
            system_name=config['rithmic']['system_name'],
            app_name=config['rithmic']['app_name'],
            app_version=config['rithmic']['app_version'],
            gateway=gateway
        )
        
        print("Connecting to Rithmic...")
        await client.connect()
        print("✅ Connected to Rithmic")
        
        # Test with a small data request
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)  # Just 1 hour
        
        print(f"Requesting 1 hour of NQZ24 minute bars...")
        print(f"From: {start_time}")
        print(f"To: {end_time}")
        
        try:
            bars = await client.get_historical_time_bars(
                "NQZ24",
                "CME", 
                start_time,
                end_time,
                TimeBarType.MINUTE_BAR,
                1
            )
            
            print(f"📊 Received {len(bars) if bars else 0} bars")
            
            if bars and len(bars) > 0:
                print("\n📋 First bar structure:")
                first_bar = bars[0]
                if isinstance(first_bar, dict):
                    for key, value in first_bar.items():
                        print(f"   {key}: {value} ({type(value).__name__})")
                else:
                    print(f"   Bar type: {type(first_bar)}")
                    print(f"   Bar attributes: {dir(first_bar)}")
                
                print(f"\n📋 Sample bar data (first 3 bars):")
                for i, bar in enumerate(bars[:3]):
                    if isinstance(bar, dict):
                        timestamp = bar.get('bar_end_datetime', 'Unknown')
                        open_price = bar.get('open', 'N/A')
                        close_price = bar.get('close', 'N/A')
                        volume = bar.get('volume', 'N/A')
                        print(f"   Bar {i+1}: {timestamp} O:{open_price} C:{close_price} V:{volume}")
                    else:
                        print(f"   Bar {i+1}: {bar}")
            else:
                print("⚠️  No bars received - this could be the issue!")
                print("   Possible reasons:")
                print("   - Market closed during requested time")
                print("   - No trading activity for NQZ24")
                print("   - Contract may have expired")
                print("   - Wrong exchange or symbol")
                
        except Exception as e:
            print(f"❌ Error fetching bars: {e}")
            
        await client.disconnect()
        print("✅ Disconnected from Rithmic")
        
    except Exception as e:
        print(f"❌ Rithmic test failed: {e}")
        logger.exception("Rithmic test failed")

if __name__ == "__main__":
    async def main():
        success = await debug_database_insertion()
        
        if success:
            print("\n" + "="*60)
            test_rithmic = input("Would you like to test Rithmic data format? (y/n): ")
            if test_rithmic.lower() == 'y':
                await test_rithmic_data_format()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Debug session interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logging.exception("Unexpected error in debug script")