import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional, Dict, Any
import os
from urllib.parse import quote_plus
from datetime import datetime, timezone

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
import pandas as pd

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Manages database connection configuration, loading from environment variables."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config:
            self.config = config
        else:
            self.config = self._load_from_environment()

    def _load_from_environment(self) -> Dict[str, Any]:
        """Loads database configuration from environment variables."""
        init_mode = os.getenv('DB_INIT_MODE', 'False').lower() == 'true'
        if init_mode:
            user = os.getenv('POSTGRES_ADMIN_USER', 'trading_admin')
            password = os.getenv('POSTGRES_ADMIN_PASSWORD', 'myAdmin4Tr4ding42!')
        else:
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
        """Returns the synchronous database connection URL."""
        password = quote_plus(self.config['password'])
        return (
            f"postgresql://{self.config['username']}:{password}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )

    def get_async_url(self) -> str:
        """Returns the asynchronous database connection URL."""
        password = quote_plus(self.config['password'])
        return (
            f"postgresql+asyncpg://{self.config['username']}:{password}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )

class DatabaseManager:
    """Manages synchronous and asynchronous database engines and sessions."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.db_config = DatabaseConfig(config)
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None

    def get_sync_engine(self):
        """Gets or creates the synchronous SQLAlchemy engine."""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.db_config.get_sync_url(),
                pool_size=self.db_config.config['pool_size'],
                max_overflow=self.db_config.config['max_overflow'],
                pool_timeout=self.db_config.config['pool_timeout'],
                pool_recycle=self.db_config.config['pool_recycle'],
                echo=self.db_config.config['echo'],
                connect_args={
                    "application_name": "futures_trading_system",
                    "options": "-c timezone=UTC"
                }
            )
        return self._sync_engine

    def get_async_engine(self):
        """Gets or creates the asynchronous SQLAlchemy engine."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.db_config.get_async_url(),
                pool_size=self.db_config.config['pool_size'],
                max_overflow=self.db_config.config['max_overflow'],
                pool_timeout=self.db_config.config['pool_timeout'],
                pool_recycle=self.db_config.config['pool_recycle'],
                echo=self.db_config.config['echo'],
                connect_args={
                    "server_settings": {
                        "timezone": "UTC",
                        "application_name": "futures_trading_system"
                    }
                }
            )
        return self._async_engine

    def get_sync_session_factory(self):
        """Gets or creates the synchronous session factory."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.get_sync_engine(),
                expire_on_commit=False
            )
        return self._sync_session_factory

    def get_async_session_factory(self):
        """Gets or creates the asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.get_async_engine(),
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_factory

    @contextmanager
    def get_sync_session(self) -> Generator[Session, None, None]:
        """Provides a synchronous database session with automatic commit/rollback."""
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
        """Provides an asynchronous database session with automatic commit/rollback."""
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
        """Tests the database connection."""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def initialize_database_schema(self):
        """
        Initializes the database by creating extensions, tables, hypertables,
        and setting up retention policies.
        """
        try:
            async with self.get_async_session() as session:
                logger.info("Creating TimescaleDB and other extensions...")
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"))
                logger.info("Extensions created/verified.")

                logger.info("Creating market_data_seconds table...")
                await session.execute(text("""
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
                """))
                logger.info("market_data_seconds table created/verified.")

                logger.info("Creating market_data_minutes table...")
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS market_data_minutes (
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
                        avg_spread DECIMAL(12,4),
                        max_spread DECIMAL(12,4),
                        trade_count INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (timestamp, symbol, contract, exchange)
                    );
                """))
                logger.info("market_data_minutes table created/verified.")

                logger.info("Creating raw_tick_data table...")
                await session.execute(text("""
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
                """))
                logger.info("raw_tick_data table created/verified.")
                
                logger.info("Creating features table...")
                await session.execute(text("""
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
                """))
                logger.info("features table created/verified.")

                logger.info("Creating predictions table...")
                await session.execute(text("""
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
                """))
                logger.info("predictions table created/verified.")

                logger.info("Creating trades table...")
                await session.execute(text("CREATE SEQUENCE IF NOT EXISTS trades_trade_id_seq;"))
                await session.execute(text("""
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
                """))
                logger.info("trades table created/verified.")

                logger.info("Converting tables to hypertables...")
                hypertables_to_create = [
                    {'table': 'market_data_seconds', 'time_column': 'timestamp', 'chunk_interval': "INTERVAL '1 minute'"},
                    {'table': 'raw_tick_data', 'time_column': 'timestamp', 'chunk_interval': "INTERVAL '10 seconds'"},
                    {'table': 'market_data_minutes', 'time_column': 'timestamp', 'chunk_interval': "INTERVAL '1 hour'"},
                    {'table': 'features', 'time_column': 'timestamp', 'chunk_interval': "INTERVAL '1 day'"},
                    {'table': 'predictions', 'time_column': 'timestamp', 'chunk_interval': "INTERVAL '1 day'"},
                    {'table': 'trades', 'time_column': 'timestamp', 'chunk_interval': "INTERVAL '1 day'"}
                ]
                for ht in hypertables_to_create:
                    try:
                        await session.execute(text(f"""
                            SELECT create_hypertable('{ht['table']}', '{ht['time_column']}',
                            chunk_time_interval => {ht['chunk_interval']}, if_not_exists => TRUE);
                        """))
                        logger.info(f"Hypertable '{ht['table']}' created/verified.")
                    except Exception as e:
                        logger.warning(f"Could not create hypertable '{ht['table']}': {e}")
                
                logger.info("Creating indexes...")
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
                        await session.execute(text(idx_sql))
                    except Exception as e:
                        logger.warning(f"Could not create index: {e}")
                logger.info("Indexes created/verified.")

                logger.info("Setting up retention policies...")
                retention_policies = [
                    {'table': 'raw_tick_data', 'interval': "INTERVAL '7 days'"},
                    {'table': 'market_data_seconds', 'interval': "INTERVAL '1 year'"},
                    {'table': 'market_data_minutes', 'interval': "INTERVAL '2 years'"},
                    {'table': 'predictions', 'interval': "INTERVAL '6 months'"}
                ]
                for policy in retention_policies:
                    try:
                        # Check if retention policy already exists to avoid error
                        policy_exists = await session.execute(text(f"""
                            SELECT EXISTS (
                                SELECT 1 FROM timescaledb_information.drop_chunks_policies
                                WHERE hypertable_name = '{policy['table']}'
                            );
                        """))
                        if not policy_exists.scalar():
                            await session.execute(text(f"SELECT add_retention_policy('{policy['table']}', {policy['interval']});"))
                            logger.info(f"Added retention policy for {policy['table']}: {policy['interval']}")
                        else:
                            logger.info(f"Retention policy for {policy['table']} already exists.")
                    except Exception as e:
                        logger.warning(f"Could not set retention policy for {policy['table']}: {e}")
                logger.info("Retention policies configured.")

                await session.commit() # Commit all schema changes

        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise

    async def verify_tables(self) -> bool:
        """Verifies that all required tables exist in the database."""
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
                logger.info("All required tables exist.")
                return True
        except Exception as e:
            logger.error(f"Error verifying tables: {e}")
            return False

    async def verify_hypertables(self) -> bool:
        """Verifies that hypertables are correctly set up."""
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
        """Closes all database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """Provides a singleton instance of the DatabaseManager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    return _db_manager

@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager for synchronous database sessions."""
    with get_database_manager().get_sync_session() as session:
        yield session

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for asynchronous database sessions."""
    async with get_database_manager().get_async_session() as session:
        yield session

class TimescaleDBHelper:
    """Helper class for TimescaleDB-specific data operations."""
    def __init__(self, session):
        self.session = session

    async def bulk_insert_market_data(self, data: list, table_name: str) -> None:
        """
        Bulk inserts market data, updating on conflict.
        """
        if not data:
            return

        try:
            # Get column names from the first record to build the SQL dynamically
            # Ensure all records have consistent keys or handle missing keys with None
            columns = list(data[0].keys())
            
            # Construct the ON CONFLICT DO UPDATE SET clause dynamically
            update_set_clauses = []
            for col in columns:
                # Skip primary key columns in the UPDATE SET clause
                if col not in ['timestamp', 'symbol', 'contract', 'exchange', 'sequence_number', 'trade_id']:
                    update_set_clauses.append(f"{col} = EXCLUDED.{col}")
            
            # Determine the primary key columns for ON CONFLICT clause based on table
            if table_name == 'market_data_seconds' or table_name == 'market_data_minutes' or table_name == 'features' or table_name == 'predictions':
                conflict_columns = "(timestamp, symbol, contract, exchange)"
            elif table_name == 'raw_tick_data':
                conflict_columns = "(timestamp, symbol, contract, exchange, sequence_number)"
            elif table_name == 'trades':
                conflict_columns = "(timestamp, trade_id)" # Assuming trade_id is part of PK for trades
            else:
                logger.warning(f"Unknown table_name '{table_name}' for ON CONFLICT clause. Using default (timestamp, symbol).")
                conflict_columns = "(timestamp, symbol)"

            sql = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join([f':{col}' for col in columns])})
                ON CONFLICT {conflict_columns} DO UPDATE SET
                    {', '.join(update_set_clauses)}
            """
            
            # Execute in a single transaction for efficiency
            await self.session.execute(text(sql), data)
            logger.info(f"Bulk inserted/updated {len(data)} records to {table_name}")
            await self.session.commit() # Explicit commit for bulk operation

        except Exception as e:
            logger.error(f"Error in bulk insert/update to {table_name}: {e}")
            await self.session.rollback() # Rollback on error
            raise

    async def get_latest_data(self, symbol: str, exchange: Optional[str] = None,
                            table_name: str = 'market_data_seconds', limit: int = 100) -> pd.DataFrame:
        """Retrieves the latest market data for a given symbol and exchange."""
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
        """Inserts a single second bar record."""
        try:
            await self.bulk_insert_market_data([record], table_name)
            logger.debug(f"Inserted 1 record to {table_name}")
        except Exception as e:
            logger.error(f"Error inserting record to {table_name}: {e}")
            raise

    async def get_volume_by_exchange(self, symbol: str, date: Optional[str] = None) -> pd.DataFrame:
        """Retrieves volume statistics by exchange for a given symbol and date."""
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
    """Manages exchange-specific data operations."""
    def __init__(self, session):
        self.session = session
        self.timescale_helper = TimescaleDBHelper(session)

    async def get_exchange_rankings(self, symbol: str) -> Dict[str, Dict]:
        """Retrieves current exchange rankings by volume for a given symbol."""
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
        """Finds potential arbitrage opportunities between exchanges for a given symbol."""
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

async def test_database_setup():
    """Tests the database setup and basic operations."""
    try:
        db_manager = get_database_manager()
        connection_ok = await db_manager.test_connection()
        if not connection_ok:
            logger.error("[ERROR] Database connection failed")
            return False
        logger.info("[SUCCESS] Database connection successful")

        # Use the new combined schema initialization
        await db_manager.initialize_database_schema()
        logger.info("[SUCCESS] Database schema initialized/verified")

        tables_ok = await db_manager.verify_tables()
        if not tables_ok:
            logger.error("[ERROR] Required tables missing")
            return False
        logger.info("[SUCCESS] All tables verified")

        hypertables_ok = await db_manager.verify_hypertables()
        if not hypertables_ok:
            logger.warning("[WARNING] No hypertables found or verification failed - may need fresh setup or review.")
        else:
            logger.info("[SUCCESS] Hypertables verified")

        async with get_async_session() as session:
            test_data = [{
                'timestamp': datetime.now(timezone.utc), # Ensure timezone-aware datetime
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
            await helper.bulk_insert_market_data(test_data, 'market_data_seconds')
            logger.info("[SUCCESS] Test data insertion successful")

            latest_data = await helper.get_latest_data('NQ', 'CME', limit=1)
            if not latest_data.empty:
                logger.info(f"[SUCCESS] Test data retrieval successful: {len(latest_data)} records")
            else:
                logger.warning("[WARNING] No data retrieved in test")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Database setup test failed: {e}")
        return False

def get_production_config() -> Dict[str, Any]:
    """Returns production database configuration."""
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
    """Returns development database configuration."""
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

