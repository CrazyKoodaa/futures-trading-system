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
        try:
            async with self.get_async_session() as session:
                # Create TimescaleDB extension
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                # Create additional extensions
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"))
                logger.info("Database extensions initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    async def create_tables(self):
        """Create all required tables before creating hypertables"""
        tables_sql = [
            # Market data seconds table
            """
            CREATE TABLE IF NOT EXISTS market_data_seconds (
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
            """,
            # Raw tick data table
            """
            CREATE TABLE IF NOT EXISTS raw_tick_data (
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
            """,
            # Market data minutes table
            """
            CREATE TABLE IF NOT EXISTS market_data_minutes (
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
            """,
            # Features table
            """
            CREATE TABLE IF NOT EXISTS features (
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
            """,
            # Predictions table
            """
            CREATE TABLE IF NOT EXISTS predictions (
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
            """,
            # Trades table
            """
            CREATE TABLE IF NOT EXISTS trades (
                trade_id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
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
            """
        ]

        try:
            async with self.get_async_session() as session:
                for sql in tables_sql:
                    await session.execute(text(sql))
                    await session.commit()
                logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    async def create_hypertables(self):
        """Create TimescaleDB hypertables for time-series data"""
        hypertables = [
            {
                'table': 'market_data_seconds',
                'time_column': 'timestamp',
                'chunk_interval': "INTERVAL '1 minute'"
            },
            {
                'table': 'raw_tick_data',
                'time_column': 'timestamp',
                'chunk_interval': "INTERVAL '10 seconds'"
            },
            {
                'table': 'market_data_minutes',
                'time_column': 'timestamp',
                'chunk_interval': "INTERVAL '1 hour'"
            },
            {
                'table': 'features',
                'time_column': 'timestamp',
                'chunk_interval': "INTERVAL '1 day'"
            },
            {
                'table': 'predictions',
                'time_column': 'timestamp',
                'chunk_interval': "INTERVAL '1 day'"
            },
            {
                'table': 'trades',
                'time_column': 'timestamp',
                'chunk_interval': "INTERVAL '1 day'"
            }
        ]

        async with self.get_async_session() as session:
            for hypertable in hypertables:
                try:
                    # Check if table exists and is not already a hypertable
                    check_sql = text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = :table_name
                        ) AND NOT EXISTS (
                            SELECT FROM timescaledb_information.hypertables 
                            WHERE hypertable_name = :table_name
                        );
                    """)
                    
                    result = await session.execute(check_sql, {'table_name': hypertable['table']})
                    should_create = result.scalar()
                    
                    if should_create:
                        query = text(f"""
                            SELECT create_hypertable('{hypertable['table']}', '{hypertable['time_column']}',
                            chunk_time_interval => {hypertable['chunk_interval']}, if_not_exists => TRUE);
                        """)
                        await session.execute(query)
                        await session.commit()
                        logger.info(f"Created hypertable: {hypertable['table']}")
                    else:
                        logger.info(f"Hypertable {hypertable['table']} already exists or table not found")
                        
                except Exception as e:
                    logger.warning(f"Could not create hypertable {hypertable['table']}: {e}")
                    # Don't rollback here, continue with other hypertables

    async def setup_retention_policies(self):
        """Set up data retention policies"""
        retention_policies = [
            {'table': 'raw_tick_data', 'interval': "INTERVAL '7 days'"},
            {'table': 'market_data_seconds', 'interval': "INTERVAL '1 year'"},
            {'table': 'market_data_minutes', 'interval': "INTERVAL '2 years'"},
            {'table': 'predictions', 'interval': "INTERVAL '6 months'"}
        ]

        async with self.get_async_session() as session:
            for policy in retention_policies:
                try:
                    # Check if table is a hypertable before adding retention policy
                    check_sql = text("""
                        SELECT EXISTS (
                            SELECT FROM timescaledb_information.hypertables 
                            WHERE hypertable_name = :table_name
                        );
                    """)
                    
                    result = await session.execute(check_sql, {'table_name': policy['table']})
                    is_hypertable = result.scalar()
                    
                    if is_hypertable:
                        query = text(f"SELECT add_retention_policy('{policy['table']}', {policy['interval']});")
                        await session.execute(query)
                        await session.commit()
                        logger.info(f"Added retention policy for {policy['table']}: {policy['interval']}")
                    else:
                        logger.warning(f"Skipping retention policy for {policy['table']} - not a hypertable")
                        
                except Exception as e:
                    logger.warning(f"Retention policy for {policy['table']} may already exist: {e}")

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
            # Convert to DataFrame for efficient insertion
            df = pd.DataFrame(data)
            # Use pandas to_sql with method='multi' for bulk insert
            if hasattr(self.session, 'connection'):
                # Sync session
                df.to_sql(table_name, self.session.connection(),
                         if_exists='append', index=False, method='multi')
            else:
                # Async session - use raw connection
                connection = await self.session.connection()
                df.to_sql(table_name, connection.sync_connection,
                         if_exists='append', index=False, method='multi')
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
        if hasattr(self.session, 'execute'):
            # Async session
            result = await self.session.execute(text(query), params)
            data = result.fetchall()
        else:
            # Sync session
            result = self.session.execute(text(query), params)
            data = result.fetchall()
        if data:
            return pd.DataFrame([dict(row._mapping) for row in data])
        else:
            return pd.DataFrame()

    async def insert_second_data(self, record: Dict[str, Any], table_name: str = 'market_data_seconds') -> None:
        try:
            # Use bulk_insert_market_data with a single record
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
        if hasattr(self.session, 'execute'):
            result = await self.session.execute(text(query), params)
        else:
            result = self.session.execute(text(query), params)
        data = result.fetchall()
        return pd.DataFrame([dict(row._mapping) for row in data])

class ExchangeDataManager:
    def __init__(self, session):
        self.session = session
        self.timescale_helper = TimescaleDBHelper(session)

    async def get_exchange_rankings(self, symbol: str) -> Dict[str, Dict]:
        volume_data = await self.timescale_helper.get_volume_by_exchange(symbol)
        rankings = {}
        # Use enumerate to get a proper integer index
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
        if hasattr(self.session, 'execute'):
            result = await self.session.execute(text(query), {'symbol': symbol, 'threshold': threshold})
        else:
            result = self.session.execute(text(query), {'symbol': symbol, 'threshold': threshold})
        data = result.fetchall()
        return pd.DataFrame([dict(row._mapping) for row in data])

# Example usage and testing functions
async def test_database_setup():
    try:
        # Test connection
        db_manager = get_database_manager()
        connection_ok = await db_manager.test_connection()
        if not connection_ok:
            logger.error("[ERROR] Database connection failed")
            return False
        logger.info("[SUCCESS] Database connection successful")

        # Initialize database
        await db_manager.initialize_database()
        logger.info("[SUCCESS] Database extensions initialized")

        # Create tables first
        await db_manager.create_tables()
        logger.info("[SUCCESS] Tables created")

        # Create hypertables
        await db_manager.create_hypertables()
        logger.info("[SUCCESS] Hypertables created")

        # Set up retention policies
        await db_manager.setup_retention_policies()
        logger.info("[SUCCESS] Retention policies configured")

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