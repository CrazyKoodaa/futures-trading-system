import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional, Dict, Any
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
import pandas as pd

logger = logging.getLogger(__name__)

class DatabaseConfig:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config:
            self.config = config
        else:
            self.config = self._load_from_environment()

    def _load_from_environment(self) -> Dict[str, Any]:
        init_mode = os.getenv('DB_INIT_MODE', 'False').lower() == 'true'
        if init_mode:
            # Use admin credentials for initialization
            user = os.getenv('POSTGRES_ADMIN_USER', 'trading_admin')
            password = os.getenv('POSTGRES_ADMIN_PASSWORD', 'myAdmin4Tr4ding42!')
        else:
            # Use regular user for normal operations
            user = os.getenv('POSTGRES_USER', 'trading_user')
            password = os.getenv('POSTGRES_PASSWORD', 'myData4Tr4ding42!')

        return {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'trading_db'),
            'username': user,
            'password': password,
            'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
            'echo': os.getenv('DB_ECHO', 'False').lower() == 'true'
        }

    def get_sync_url(self) -> str:
        password = quote_plus(self.config['password'])
        return (
            f"postgresql://{self.config['username']}:{password}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )

    def get_async_url(self) -> str:
        password = quote_plus(self.config['password'])
        return (
            f"postgresql+asyncpg://{self.config['username']}:{password}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )

class DatabaseManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.db_config = DatabaseConfig(config)
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None

    def get_sync_engine(self):
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.db_config.get_sync_url(),
                pool_size=self.db_config.config['pool_size'],
                max_overflow=self.db_config.config['max_overflow'],
                pool_timeout=self.db_config.config['pool_timeout'],
                pool_recycle=self.db_config.config['pool_recycle'],
                echo=self.db_config.config['echo'],
                # TimescaleDB optimizations
                connect_args={
                    "application_name": "futures_trading_system",
                    "options": "-c timezone=UTC"
                }
            )
        return self._sync_engine

    def get_async_engine(self):
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.db_config.get_async_url(),
                pool_size=self.db_config.config['pool_size'],
                max_overflow=self.db_config.config['max_overflow'],
                pool_timeout=self.db_config.config['pool_timeout'],
                pool_recycle=self.db_config.config['pool_recycle'],
                echo=self.db_config.config['echo'],
                # AsyncPG specific options
                connect_args={
                    "server_settings": {
                        "timezone": "UTC",
                        "application_name": "futures_trading_system"
                    }
                }
            )
        return self._async_engine

    def get_sync_session_factory(self):
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.get_sync_engine(),
                expire_on_commit=False
            )
        return self._sync_session_factory

    def get_async_session_factory(self):
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.get_async_engine(),
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory

    @contextmanager
    def get_sync_session(self) -> Generator[Session, None, None]:
        session = self.get_sync_session_factory()()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error in sync session: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        session = self.get_async_session_factory()()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error in async session: {e}")
            raise
        finally:
            await session.close()

    async def test_connection(self) -> bool:
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def initialize_database(self):
        """Simple database initialization - just check if everything is ready"""
        try:
            async with self.get_async_session() as session:
                # Test that TimescaleDB extension exists
                result = await session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb';"))
                if not result.scalar():
                    logger.error("TimescaleDB extension not found!")
                    raise Exception("TimescaleDB extension not installed")
                    
                logger.info("Database is ready and TimescaleDB is available")
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            raise

    async def verify_tables(self):
        """Verify that all required tables exist"""
        required_tables = [
            'market_data_seconds',
            'raw_tick_data', 
            'market_data_minutes',
            'features',
            'predictions',
            'trades'
        ]
        
        try:
            async with self.get_async_session() as session:
                for table in required_tables:
                    result = await session.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table}'
                        );
                    """))
                    
                    if not result.scalar():
                        logger.error(f"Required table '{table}' not found!")
                        return False
                        
                logger.info("All required tables exist")
                return True
                
        except Exception as e:
            logger.error(f"Error verifying tables: {e}")
            return False

    async def verify_hypertables(self):
        """Verify that hypertables are properly configured"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("""
                    SELECT hypertable_name, num_chunks
                    FROM timescaledb_information.hypertables
                    ORDER BY hypertable_name;
                """))
                
                hypertables = result.fetchall()
                logger.info(f"Found {len(hypertables)} hypertables:")
                for ht in hypertables:
                    logger.info(f"  - {ht[0]} ({ht[1]} chunks)")
                    
                return len(hypertables) > 0
                
        except Exception as e:
            logger.error(f"Error verifying hypertables: {e}")
            return False

    async def close_connections(self):
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    return _db_manager

# Convenience functions for common usage patterns
@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    with get_database_manager().get_sync_session() as session:
        yield session

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_database_manager().get_async_session() as session:
        yield session

class TimescaleDBHelper:
    def __init__(self, session):
        self.session = session

    async def bulk_insert_market_data(self, data: list, table_name: str = 'market_data_seconds'):
        if not data:
            return
            
        try:
            # Simple approach: insert records one by one for reliability
            for record in data:
                # Convert pandas Timestamp to datetime if needed
                processed_record = {}
                for key, value in record.items():
                    if isinstance(value, pd.Timestamp):
                        processed_record[key] = value.to_pydatetime()
                    elif pd.isna(value):
                        processed_record[key] = None
                    else:
                        processed_record[key] = value
                
                # Build column list and placeholder list
                columns = list(processed_record.keys())
                placeholders = [f":{col}" for col in columns]
                
                sql = f"""
                    INSERT INTO {table_name} ({', '.join(columns)}) 
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT DO NOTHING
                """
                
                await self.session.execute(text(sql), processed_record)
            
            logger.debug(f"Bulk inserted {len(data)} records to {table_name}")
                
        except Exception as e:
            logger.error(f"Error in bulk insert to {table_name}: {e}")
            raise

    async def get_latest_data(self, symbol: str, exchange: Optional[str] = None,
                            table_name: str = 'market_data_seconds', limit: int = 100) -> pd.DataFrame:
        query = f"""
            SELECT * FROM {table_name}
            WHERE symbol = :symbol
            {f"AND exchange = :exchange" if exchange else ""}
            ORDER BY timestamp DESC
            LIMIT :limit
        """
        params = {'symbol': symbol, 'limit': limit}
        if exchange:
            params['exchange'] = exchange
            
        result = await self.session.execute(text(query), params)
        data = result.fetchall()
        
        if data:
            return pd.DataFrame([dict(row._mapping) for row in data])
        else:
            return pd.DataFrame()

    async def insert_second_data(self, record: Dict[str, Any], table_name: str = 'market_data_seconds') -> None:
        try:
            await self.bulk_insert_market_data([record], table_name)
            logger.debug(f"Inserted 1 record to {table_name}")
        except Exception as e:
            logger.error(f"Error inserting record to {table_name}: {e}")
            raise

    async def get_volume_by_exchange(self, symbol: str, date: Optional[str] = None) -> pd.DataFrame:
        date_filter = f"AND DATE(timestamp) = :date" if date else ""
        query = f"""
            SELECT
                exchange,
                SUM(volume) as total_volume,
                COUNT(*) as bar_count,
                AVG(spread) as avg_spread,
                MIN(timestamp) as first_bar,
                MAX(timestamp) as last_bar
            FROM market_data_seconds
            WHERE symbol = :symbol {date_filter}
            GROUP BY exchange
            ORDER BY total_volume DESC
        """
        params = {'symbol': symbol}
        if date:
            params['date'] = date
            
        result = await self.session.execute(text(query), params)
        data = result.fetchall()
        return pd.DataFrame([dict(row._mapping) for row in data])

class ExchangeDataManager:
    def __init__(self, session):
        self.session = session
        self.timescale_helper = TimescaleDBHelper(session)

    async def get_exchange_rankings(self, symbol: str) -> Dict[str, Dict]:
        volume_data = await self.timescale_helper.get_volume_by_exchange(symbol)
        rankings = {}
        
        for idx, (_, row) in enumerate(volume_data.iterrows()):
            rankings[row['exchange']] = {
                'rank': idx + 1,
                'total_volume': int(row['total_volume']),
                'bar_count': row['bar_count'],
                'avg_spread': float(row['avg_spread']) if row['avg_spread'] else 0,
                'market_share': float(row['total_volume']) / float(volume_data['total_volume'].sum()) * 100
            }
        return rankings

    async def get_cross_exchange_arbitrage_opportunities(self, symbol: str,
                                                       threshold: float = 0.5) -> pd.DataFrame:
        query = """
            SELECT
                a.timestamp,
                a.exchange as exchange_a,
                b.exchange as exchange_b,
                a.close as price_a,
                b.close as price_b,
                ABS(a.close - b.close) as price_diff,
                (ABS(a.close - b.close) / ((a.close + b.close) / 2)) * 100 as price_diff_pct
            FROM market_data_seconds a
            JOIN market_data_seconds b ON a.timestamp = b.timestamp
                AND a.symbol = b.symbol
                AND a.exchange != b.exchange
            WHERE a.symbol = :symbol
                AND a.timestamp >= NOW() - INTERVAL '1 hour'
                AND (ABS(a.close - b.close) / ((a.close + b.close) / 2)) * 100 >= :threshold
            ORDER BY a.timestamp DESC, price_diff_pct DESC
            LIMIT 100
        """
        
        result = await self.session.execute(text(query), {'symbol': symbol, 'threshold': threshold})
        data = result.fetchall()
        return pd.DataFrame([dict(row._mapping) for row in data])

# Main test function - simplified without retention policies
async def test_database_setup():
    try:
        # Test connection
        db_manager = get_database_manager()
        connection_ok = await db_manager.test_connection()
        if not connection_ok:
            logger.error("[ERROR] Database connection failed")
            return False
        logger.info("[SUCCESS] Database connection successful")

        # Initialize database (just check readiness)
        await db_manager.initialize_database()
        logger.info("[SUCCESS] Database is ready")

        # Verify tables exist
        tables_ok = await db_manager.verify_tables()
        if not tables_ok:
            logger.error("[ERROR] Required tables missing")
            return False
        logger.info("[SUCCESS] All tables verified")

        # Verify hypertables
        hypertables_ok = await db_manager.verify_hypertables()
        if not hypertables_ok:
            logger.warning("[WARNING] No hypertables found - may need fresh setup")
        else:
            logger.info("[SUCCESS] Hypertables verified")

        # Test data operations
        async with get_async_session() as session:
            # Test market data insertion
            test_data = [{
                'timestamp': pd.Timestamp.now(),
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
            
            helper = TimescaleDBHelper(session)
            await helper.bulk_insert_market_data(test_data)
            logger.info("[SUCCESS] Test data insertion successful")
            
            # Test data retrieval
            latest_data = await helper.get_latest_data('NQ', 'CME', limit=1)
            if not latest_data.empty:
                logger.info(f"[SUCCESS] Test data retrieval successful: {len(latest_data)} records")
            else:
                logger.warning("[WARNING] No data retrieved in test")
                
        return True
    except Exception as e:
        logger.error(f"[ERROR] Database setup test failed: {e}")
        return False

# Configuration for different environments
def get_production_config() -> Dict[str, Any]:
    return {
        'host': os.getenv('PROD_POSTGRES_HOST', 'production-timescaledb'),
        'port': int(os.getenv('PROD_POSTGRES_PORT', '5432')),
        'database': os.getenv('PROD_POSTGRES_DB', 'trading_db'),
        'username': os.getenv('PROD_POSTGRES_USER', 'trading_user'),
        'password': os.getenv('PROD_POSTGRES_PASSWORD'),
        'pool_size': 20,
        'max_overflow': 40,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'echo': False
    }

def get_development_config() -> Dict[str, Any]:
    return {
        'host': os.getenv('DEV_POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('DEV_POSTGRES_PORT', '5432')),
        'database': os.getenv('DEV_POSTGRES_DB', 'trading_db_dev'),
        'username': os.getenv('DEV_POSTGRES_USER', 'trading_user'),
        'password': os.getenv('DEV_POSTGRES_PASSWORD', 'dev_password'),
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'echo': True
    }

if __name__ == "__main__":
    import asyncio
    async def main():
        success = await test_database_setup()
        if success:
            print("🎉 Database setup completed successfully!")
        else:
            print("❌ Database setup failed!")
    asyncio.run(main())