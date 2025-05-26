#!/usr/bin/env python3
"""
TimescaleDB Setup Script for Futures Trading System
Ensures proper database initialization with all required tables and hypertables
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database.connection import get_database_manager, get_async_session, TimescaleDBHelper
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def setup_timescale_database():
    """Complete TimescaleDB setup for futures trading system"""
    print("🚀 Setting up TimescaleDB for Futures Trading System")
    print("=" * 60)
    
    try:
        # Step 1: Test connection
        print("1. Testing database connection...")
        db_manager = get_database_manager()
        connection_ok = await db_manager.test_connection()
        
        if not connection_ok:
            print("❌ Database connection failed!")
            print("Make sure:")
            print("   - PostgreSQL is running")
            print("   - Database credentials are correct in .env file")
            print("   - TimescaleDB extension is installed")
            return False
        
        print("✅ Database connection successful")
        
        # Step 2: Initialize extensions
        print("\n2. Creating TimescaleDB extensions...")
        await db_manager.initialize_database()
        print("✅ Extensions created successfully")
        
        # Step 3: Create tables and hypertables
        print("\n3. Creating tables and hypertables...")
        async with get_async_session() as session:
            # Create market_data_seconds table if not exists
            await session.execute(text("""
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
                    data_quality_score DOUBLE PRECISION DEFAULT 1.0,
                    is_regular_hours BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            
            # Create market_data_minutes table if not exists
            await session.execute(text("""
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
                    data_quality_score DOUBLE PRECISION DEFAULT 1.0,
                    is_regular_hours BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            
            await session.commit()
            print("✅ Tables created successfully")
        
        # Step 4: Create hypertables
        print("\n4. Converting to hypertables...")
        await db_manager.create_hypertables()
        print("✅ Hypertables created successfully")
        
        # Step 5: Create indexes
        print("\n5. Creating indexes for performance...")
        async with get_async_session() as session:
            # Indexes for market_data_seconds
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_market_data_seconds_symbol_time 
                ON market_data_seconds (symbol, exchange, timestamp DESC);
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_market_data_seconds_contract_time 
                ON market_data_seconds (contract, timestamp DESC);
            """))
            
            # Indexes for market_data_minutes
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_market_data_minutes_symbol_time 
                ON market_data_minutes (symbol, exchange, timestamp DESC);
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_market_data_minutes_contract_time 
                ON market_data_minutes (contract, timestamp DESC);
            """))
            
            await session.commit()
            print("✅ Indexes created successfully")
        
        # Step 6: Set up retention policies
        print("\n6. Setting up data retention policies...")
        await db_manager.setup_retention_policies()
        print("✅ Retention policies configured")
        
        # Step 7: Insert test data
        print("\n7. Inserting test data...")
        async with get_async_session() as session:
            helper = TimescaleDBHelper(session)
            
            test_data = [{
                'timestamp': datetime.now(),
                'symbol': 'NQ',
                'contract': 'NQZ24',
                'exchange': 'CME',
                'exchange_code': 'XCME',
                'open': 17245.50,
                'high': 17246.00,
                'low': 17245.25,
                'close': 17245.75,
                'volume': 150,
                'tick_count': 12,
                'vwap': 17245.68,
                'bid': 17245.50,
                'ask': 17245.75,
                'spread': 0.25,
                'data_quality_score': 1.0,
                'is_regular_hours': True
            }]
            
            await helper.bulk_insert_market_data(test_data, 'market_data_seconds')
            print("✅ Test data inserted successfully")
        
        # Step 8: Verify setup
        print("\n8. Verifying setup...")
        async with get_async_session() as session:
            # Check hypertables
            result = await session.execute(text("""
                SELECT schemaname, tablename 
                FROM timescaledb_information.hypertables 
                WHERE tablename IN ('market_data_seconds', 'market_data_minutes')
            """))
            
            hypertables = result.fetchall()
            print(f"   Found {len(hypertables)} hypertables:")
            for table in hypertables:
                print(f"     - {table[1]}")
            
            # Check test data
            result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
            count = result.scalar()
            print(f"   Test records in market_data_seconds: {count}")
            
            # Check indexes
            result = await session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename IN ('market_data_seconds', 'market_data_minutes')
                AND indexname LIKE 'idx_%'
            """))
            
            indexes = result.fetchall()
            print(f"   Found {len(indexes)} custom indexes")
        
        print("\n" + "=" * 60)
        print("🎉 TimescaleDB setup completed successfully!")
        print("=" * 60)
        print("\nYour database is now ready for:")
        print("  ✅ Real-time tick data collection")
        print("  ✅ Historical data storage")
        print("  ✅ High-performance queries")
        print("  ✅ Automatic data compression")
        print("  ✅ Data retention management")
        
        print(f"\nConnection details:")
        print(f"  Host: {os.getenv('POSTGRES_HOST', 'localhost')}")
        print(f"  Port: {os.getenv('POSTGRES_PORT', '5432')}")
        print(f"  Database: {os.getenv('POSTGRES_DB', 'trading_db')}")
        print(f"  User: {os.getenv('POSTGRES_USER', 'trading_user')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        logger.exception("Database setup failed")
        return False