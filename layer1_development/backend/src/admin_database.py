"""
Database operations for the Futures Trading System Admin Tool

This module handles all database-related operations including:
- Connection testing and initialization
- TimescaleDB setup and management
- Data insertion and validation
- Statistics and reporting
- Schema management

Part of the modular admin system:
- admin_core_classes.py - Core data structures
- admin_operations.py - Main business logic
- admin_database.py (THIS FILE) - Database operations
- admin_rithmic_operations.py - Rithmic API operations
- admin_rithmic_historical.py - Historical data operations
- admin_rithmic_symbols.py - Symbol search operations
- admin_rithmic_connection.py - Connection management
- enhanced_admin_rithmic.py - Main TUI application
- admin_display_manager.py - Display management

Author: Trading System Admin Tool
Version: 1.0.0
"""

import asyncio
import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable, Any, AsyncGenerator
import pandas as pd
from contextlib import asynccontextmanager

# Import configuration module
from config.database_config import DatabaseConfig

# Import SQLAlchemy components
from sqlalchemy import text, create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
import asyncpg
from urllib.parse import quote_plus

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration is now imported from config.database_config


# Database manager singleton
class DatabaseManager:
    """Database connection manager"""

    _instance = None

    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if self._initialized:
            return

        self.db_config = DatabaseConfig(config)
        self.async_engine = create_async_engine(
            self.db_config.get_async_url(),
            echo=self.db_config.config["echo"],
            pool_size=self.db_config.config["pool_size"],
            max_overflow=self.db_config.config["max_overflow"],
            pool_timeout=self.db_config.config["pool_timeout"],
            pool_recycle=self.db_config.config["pool_recycle"],
        )
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine, expire_on_commit=False, class_=AsyncSession
        )
        self._initialized = True

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session"""
        session = self.async_session_factory()
        try:
            yield session
        finally:
            await session.close()

    async def test_connection(self) -> bool:
        """Test database connection

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection test failed: {e}")
            return False


# Get database manager singleton
def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """Get the database manager singleton instance"""
    return DatabaseManager(config)


# Async session context manager
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session using the context manager pattern"""
    async with get_database_manager().get_async_session() as session:
        yield session


# TimescaleDB helper class
class TimescaleDBHelper:
    """Helper class for TimescaleDB operations"""

    def __init__(self, session):
        self.session = session

    async def bulk_insert_market_data(self, data: list, table_name: str = "market_data_seconds"):
        """Insert market data with improved error handling and logging"""
        if not data:
            logger.warning("No data provided for insertion")
            return

        logger.info(f"Attempting to insert {len(data)} records into {table_name}")

        try:
            inserted_count = 0
            failed_count = 0

            # Execute the insert
            await self.session.execute(
                text(
                    f"INSERT INTO {table_name} (symbol, timestamp, open, high, low, close, volume) "
                    "VALUES (:symbol, :timestamp, :open, :high, :low, :close, :volume) "
                    "ON CONFLICT (symbol, timestamp) DO UPDATE SET "
                    "open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, "
                    "close = EXCLUDED.close, volume = EXCLUDED.volume"
                ),
                [dict(row) for row in data],
            )
            await self.session.commit()

            inserted_count = len(data)
            logger.info(f"Successfully inserted {inserted_count} records into {table_name}")
            return inserted_count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error inserting data into {table_name}: {str(e)}")
            raise


# Test database setup
async def test_database_setup() -> Dict[str, Any]:
    """Test the database connection and setup"""
    try:
        async with get_async_session() as session:
            # Test basic connection
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()

            if row and row[0] == 1:
                logger.info("Database connection successful")

                # Check if TimescaleDB extension is installed
                result = await session.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
                )
                has_timescale = result.fetchone() is not None

                return {
                    "success": True,
                    "message": "Database connection successful",
                    "has_timescaledb": has_timescale,
                }
            else:
                logger.error("Database connection test failed")
                return {"success": False, "message": "Database connection test failed"}
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return {"success": False, "message": f"Database connection error: {str(e)}"}


# Configure logging
logger = logging.getLogger(__name__)


class DatabaseOperations:
    """
    Handles all database operations for the admin tool
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize database operations

        Args:
            progress_callback: Optional callback function for progress reporting
        """
        self.progress_callback = progress_callback
        self.db_manager = None
        self.connection_tested = False
        self.is_initialized = False

        # Table schemas for validation
        self.table_schemas = {
            "market_data_seconds": {
                "required_columns": [
                    "timestamp",
                    "symbol",
                    "contract",
                    "exchange",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
                "primary_key": ["timestamp", "symbol", "contract", "exchange"],
            },
            "market_data_minutes": {
                "required_columns": [
                    "timestamp",
                    "symbol",
                    "contract",
                    "exchange",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
                "primary_key": ["timestamp", "symbol", "contract", "exchange"],
            },
            "raw_tick_data": {
                "required_columns": [
                    "timestamp",
                    "symbol",
                    "contract",
                    "exchange",
                    "price",
                    "size",
                    "tick_type",
                ],
                "primary_key": [
                    "timestamp",
                    "symbol",
                    "contract",
                    "exchange",
                    "sequence_number",
                ],
            },
        }

    def _report_progress(self, message: str, step: int = 0, total: int = 0):
        """Report progress if callback is available

        Args:
            message: Progress message
            step: Current step number
            total: Total steps
        """
        if self.progress_callback:
            self.progress_callback(message, step, total)
        logger.info(message)

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test database connection and basic functionality

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self._report_progress("Testing database connection...")

            # Get database manager
            self.db_manager = get_database_manager()

            # Test basic connection
            connection_ok = await self.db_manager.test_connection()
            if not connection_ok:
                return (
                    False,
                    "Failed to connect to database. Check credentials and server status.",
                )

            self._report_progress("Testing database features...")

            # Test TimescaleDB extension
            async with get_async_session() as session:
                try:
                    query_result = await session.execute(
                        text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
                    )
                    if not query_result.scalar():
                        return (
                            False,
                            "TimescaleDB extension not found. Please install TimescaleDB.",
                        )
                except Exception as e:
                    return False, f"Error checking TimescaleDB extension: {str(e)}"

                # Test permissions
                try:
                    await session.execute(text("SELECT 1"))
                    await session.execute(text("SELECT NOW()"))
                except Exception as e:
                    return False, f"Insufficient database permissions: {str(e)}"

            self.connection_tested = True
            self._report_progress("Database connection test completed successfully")

            return (
                True,
                "Database connection successful. TimescaleDB extension available.",
            )

        except Exception as e:
            error_msg = f"Database connection test failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def create_database_structure(self) -> Tuple[bool, str]:
        """
        Create the database structure including tables, indexes, and constraints

        This is a wrapper around the initialization process that focuses specifically
        on creating the database structure without test data or verification.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.connection_tested:
            success, msg = await self.test_connection()
            if not success:
                return False, f"Connection test failed: {msg}"

        try:
            total_steps = 4
            current_step = 0

            # Step 1: Initialize extensions
            current_step += 1
            self._report_progress("Creating database extensions...", current_step, total_steps)

            async with get_async_session() as session:
                try:
                    await session.execute(
                        text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                    )
                    await session.execute(
                        text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
                    )
                except Exception as e:
                    logger.warning(f"Extension creation warning: {e}")

            # Step 2: Create tables
            current_step += 1
            self._report_progress("Creating database tables...", current_step, total_steps)

            success = await self._create_tables()
            if not success:
                return False, "Failed to create database tables"

            # Step 3: Create hypertables
            current_step += 1
            self._report_progress("Converting tables to hypertables...", current_step, total_steps)

            success = await self._create_hypertables()
            if not success:
                return False, "Failed to create hypertables"

            # Step 4: Create indexes
            current_step += 1
            self._report_progress("Creating database indexes...", current_step, total_steps)

            success = await self._create_indexes()
            if not success:
                logger.warning("Some indexes could not be created")

            self._report_progress(
                "Database structure created successfully", current_step, total_steps
            )
            return True, "Database structure created successfully"

        except Exception as e:
            error_msg = f"Database structure creation failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def initialize_database(self) -> Tuple[bool, str]:
        """
        Initialize database with required tables, hypertables, and indexes

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.connection_tested:
            success, msg = await self.test_connection()
            if not success:
                return False, f"Connection test failed: {msg}"

        try:
            total_steps = 8
            current_step = 0

            # Steps 1-4: Create database structure
            structure_success, structure_msg = await self.create_database_structure()
            if not structure_success:
                return False, structure_msg

            current_step = 4  # Structure creation completed 4 steps

            # Step 5: Set up permissions
            current_step += 1
            self._report_progress("Setting up permissions...", current_step, total_steps)

            await self._setup_permissions()

            # Step 6: Insert test data
            current_step += 1
            self._report_progress("Inserting test data...", current_step, total_steps)

            await self._insert_test_data()

            # Step 7: Verify setup
            current_step += 1
            self._report_progress("Verifying database setup...", current_step, total_steps)

            verification_success, verification_msg = await self._verify_setup()
            if not verification_success:
                return False, f"Database verification failed: {verification_msg}"

            # Step 7.5: Clean up test data after successful verification
            self._report_progress("Cleaning up test data...", current_step, total_steps)
            await self._cleanup_test_data()

            # Step 8: Complete
            current_step += 1
            self._report_progress("Database initialization completed!", current_step, total_steps)

            self.is_initialized = True
            return (
                True,
                "Database initialized successfully with all required tables and indexes.",
            )

        except Exception as e:
            error_msg = f"Database initialization failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def _create_tables(self) -> bool:
        """Create all required tables"""
        try:
            async with get_async_session() as session:
                # Market data seconds table
                await session.execute(
                    text(
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
                """
                    )
                )

                # Market data minutes table
                await session.execute(
                    text(
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
                """
                    )
                )

                # Raw tick data table
                await session.execute(
                    text(
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
                        sequence_number BIGINT DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (timestamp, symbol, contract, exchange, sequence_number)
                    );
                """
                    )
                )

                # Features table
                await session.execute(
                    text(
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
                """
                    )
                )

                # Predictions table
                await session.execute(
                    text(
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
                """
                    )
                )

                # Trades table with sequence
                await session.execute(
                    text(
                        """
                    CREATE SEQUENCE IF NOT EXISTS trades_trade_id_seq;
                """
                    )
                )

                await session.execute(
                    text(
                        """
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
                """
                    )
                )

            return True

        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False

    async def _create_hypertables(self) -> bool:
        """Convert tables to TimescaleDB hypertables"""
        hypertables = [
            {"table": "market_data_seconds", "interval": "INTERVAL '1 minute'"},
            {"table": "raw_tick_data", "interval": "INTERVAL '10 seconds'"},
            {"table": "market_data_minutes", "interval": "INTERVAL '1 hour'"},
            {"table": "features", "interval": "INTERVAL '1 day'"},
            {"table": "predictions", "interval": "INTERVAL '1 day'"},
            {"table": "trades", "interval": "INTERVAL '1 day'"},
        ]

        try:
            async with get_async_session() as session:
                for ht in hypertables:
                    try:
                        await session.execute(
                            text(
                                f"""
                            SELECT create_hypertable('{ht['table']}', 'timestamp',
                            chunk_time_interval => {ht['interval']}, if_not_exists => TRUE);
                        """
                            )
                        )
                        logger.info(f"Created hypertable: {ht['table']}")
                    except Exception as e:
                        logger.warning(f"Could not create hypertable {ht['table']}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error creating hypertables: {e}")
            return False

    async def _create_indexes(self) -> bool:
        """Create performance indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_symbol_time ON market_data_seconds (symbol, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_contract_time ON market_data_seconds (contract, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_exchange_time ON market_data_seconds (exchange, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_market_data_seconds_volume ON market_data_seconds (volume DESC) WHERE volume > 0;",
            "CREATE INDEX IF NOT EXISTS idx_raw_tick_data_contract_time ON raw_tick_data (contract, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_raw_tick_data_type ON raw_tick_data (tick_type, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_features_symbol_timeframe_time ON features (symbol, timeframe, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_features_exchange_time ON features (exchange, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_predictions_symbol_model_time ON predictions (symbol, model_version, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions (confidence_score DESC) WHERE ABS(confidence_score) > 50;",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades (pnl DESC);",
            "CREATE INDEX IF NOT EXISTS idx_trades_exchange ON trades (exchange, timestamp DESC);",
        ]

        try:
            async with get_async_session() as session:
                for idx_sql in indexes:
                    try:
                        await session.execute(text(idx_sql))
                    except Exception as e:
                        logger.warning(f"Could not create index: {e}")

            return True

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False

    async def _setup_permissions(self):
        """Setup database permissions for trading_user"""
        try:
            async with get_async_session() as session:
                await session.execute(
                    text(
                        """
                    GRANT USAGE ON SCHEMA public TO trading_user;
                    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
                    GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO trading_user;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_user;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO trading_user;
                """
                    )
                )
        except Exception as e:
            logger.warning(f"Could not set up permissions: {e}")

    async def _insert_test_data(self):
        """Insert test data to verify functionality"""
        try:
            test_data = [
                {
                    "timestamp": datetime.now(),
                    "symbol": "NQ",
                    "contract": "NQZ24",
                    "exchange": "CME",
                    "exchange_code": "XCME",
                    "open": 17245.50,
                    "high": 17246.00,
                    "low": 17245.25,
                    "close": 17245.75,
                    "volume": 150,
                    "tick_count": 12,
                    "vwap": 17245.68,
                    "bid": 17245.50,
                    "ask": 17245.75,
                    "spread": 0.25,
                    "data_quality_score": 1.0,
                    "is_regular_hours": True,
                }
            ]

            await self.bulk_insert_market_data(test_data, "market_data_seconds")

        except Exception as e:
            logger.warning(f"Could not insert test data: {e}")

    async def _cleanup_test_data(self):
        """Clean up test data after verification"""
        try:
            async with get_async_session() as session:
                # Delete test data (NQ test record)
                await session.execute(
                    text(
                        """
                    DELETE FROM market_data_seconds 
                    WHERE symbol = 'NQ' 
                    AND contract = 'NQZ24' 
                    AND exchange = 'CME'
                    AND volume = 150
                    AND tick_count = 12;
                """
                    )
                )
                logger.info("Test data cleaned up successfully")
        except Exception as e:
            logger.warning(f"Could not clean up test data: {e}")

    async def cleanup(self):
        """
        Cleanup database connections and resources

        This method ensures all database connections are properly closed
        and any temporary resources are released.
        """
        logger.info("Starting database operations cleanup")

        try:
            # Close any open connections in the connection pool
            if hasattr(self, "db_manager") and self.db_manager:
                try:
                    # Close the connection pool if available
                    if hasattr(self.db_manager, "async_engine") and self.db_manager.async_engine:
                        await self.db_manager.async_engine.dispose()
                        logger.info("Database connection pool closed")
                except Exception as e:
                    logger.warning(f"Error closing database connection pool: {e}")

            # Reset any internal state
            self._report_progress("Database connections cleaned up")
            logger.info("Database operations cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            return False

    async def _verify_setup(self) -> Tuple[bool, str]:
        """Verify database setup"""
        try:
            async with get_async_session() as session:
                # Check tables
                result = await session.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """
                    )
                )
                tables = [row[0] for row in result.fetchall()]

                required_tables = [
                    "market_data_seconds",
                    "market_data_minutes",
                    "raw_tick_data",
                    "features",
                    "predictions",
                    "trades",
                ]

                missing_tables = [t for t in required_tables if t not in tables]
                if missing_tables:
                    return False, f"Missing tables: {', '.join(missing_tables)}"

                # Check hypertables
                result = await session.execute(
                    text(
                        """
                    SELECT hypertable_name, num_chunks
                    FROM timescaledb_information.hypertables
                    ORDER BY hypertable_name;
                """
                    )
                )
                hypertables = result.fetchall()

                if len(hypertables) == 0:
                    return False, "No hypertables found"

                # Check test data
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds;"))
                test_count = result.scalar()

                if test_count == 0:
                    return False, "No test data found"

                return (
                    True,
                    f"Setup verified: {len(tables)} tables, {len(hypertables)} hypertables",
                )

        except Exception as e:
            return False, f"Verification error: {str(e)}"

    async def get_database_summary(self) -> str:
        """
        Get comprehensive database summary in markdown format

        Returns:
            Formatted markdown string with database information
        """
        try:
            async with get_async_session() as session:
                summary_parts = await self._build_summary_sections(session)
                return "\n".join(summary_parts)

        except Exception as e:
            error_msg = f"Error generating database summary: {str(e)}"
            logger.error(error_msg)
            return f"# Database Summary\n\n**Error:** {error_msg}"

    async def _build_summary_sections(self, session) -> List[str]:
        """Build all sections of the database summary"""
        summary_parts = []

        # Header and connection info
        summary_parts.extend(await self._build_header_section())

        # Tables information
        summary_parts.extend(await self._build_tables_section(session))

        # Hypertables information
        summary_parts.extend(await self._build_hypertables_section(session))

        # Data statistics
        summary_parts.extend(await self._build_data_statistics_section(session))

        # Recent activity
        summary_parts.extend(await self._build_recent_activity_section(session))

        # System information
        summary_parts.extend(await self._build_system_info_section(session))

        return summary_parts

    async def _build_header_section(self) -> List[str]:
        """Build header and connection information section"""
        environment_config = os.environ
        host = environment_config.get("POSTGRES_HOST", "localhost")
        port = environment_config.get("POSTGRES_PORT", "5432")
        database = environment_config.get("POSTGRES_DB", "trading_db")
        user = environment_config.get("POSTGRES_USER", "trading_user")

        return [
            "# Database Summary",
            "",
            "## Connection Information",
            f"- **Host:** {host}:{port}",
            f"- **Database:** {database}",
            f"- **User:** {user}",
            "",
        ]

    async def _build_tables_section(self, session) -> List[str]:
        """Build tables information section"""
        result = await session.execute(
            text(
                """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
            )
        )
        tables = [row[0] for row in result.fetchall()]

        section = ["## Tables"]
        for table in tables:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                section.append(f"- **{table}:** {count:,} records")
            except Exception:
                section.append(f"- **{table}:** Error reading count")

        section.append("")
        return section

    async def _build_hypertables_section(self, session) -> List[str]:
        """Build hypertables information section"""
        try:
            result = await session.execute(
                text(
                    """
                SELECT hypertable_name, num_chunks
                FROM timescaledb_information.hypertables
                ORDER BY hypertable_name;
            """
                )
            )
            hypertables = result.fetchall()

            if hypertables:
                section = ["## TimescaleDB Hypertables"]
                for ht in hypertables:
                    section.append(f"- **{ht[0]}:** {ht[1]} chunks")
                section.append("")
                return section
        except Exception:
            pass

        return []

    async def _build_data_statistics_section(self, session) -> List[str]:
        """Build data statistics section"""
        section = []
        main_tables = ["market_data_seconds", "market_data_minutes"]

        # Get available tables first
        result = await session.execute(
            text(
                """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
            )
        )
        available_tables = [row[0] for row in result.fetchall()]

        for table in main_tables:
            if table in available_tables:
                try:
                    result = await session.execute(
                        text(
                            f"""
                        SELECT symbol, exchange, COUNT(*) as count,
                               MIN(timestamp) as first_data, MAX(timestamp) as last_data
                        FROM {table}
                        GROUP BY symbol, exchange
                        ORDER BY symbol, exchange
                        LIMIT 10;
                    """
                        )
                    )
                    data_stats = result.fetchall()

                    if data_stats:
                        section.append(f"## {table.replace('_', ' ').title()} Statistics")
                        for stat in data_stats:
                            section.append(
                                f"- **{stat[0]} ({stat[1]}):** {stat[2]:,} records "
                                f"({stat[3].strftime('%Y-%m-%d')} to {stat[4].strftime('%Y-%m-%d')})"
                            )
                        section.append("")
                except Exception:
                    pass

        return section

    async def _build_recent_activity_section(self, session) -> List[str]:
        """Build recent activity section"""
        try:
            result = await session.execute(
                text(
                    """
                SELECT timestamp, symbol, contract, exchange, close, volume
                FROM market_data_seconds
                ORDER BY timestamp DESC
                LIMIT 5;
            """
                )
            )
            recent_data = result.fetchall()

            if recent_data:
                section = ["## Recent Data Sample"]
                for data in recent_data:
                    timestamp_str = data[0].strftime("%Y-%m-%d %H:%M:%S")
                    section.append(
                        f"- **{timestamp_str}** | {data[1]} {data[2]} | "
                        f"Price: {data[4]} | Volume: {data[5]}"
                    )
                section.append("")
                return section
        except Exception:
            pass

        return []

    async def _build_system_info_section(self, session) -> List[str]:
        """Build system information section"""
        try:
            result = await session.execute(text("SELECT version()"))
            pg_version = result.scalar()

            result = await session.execute(
                text(
                    """
                SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'
            """
                )
            )
            timescale_version = result.scalar()

            section = ["## System Information"]
            section.append(
                f"- **PostgreSQL:** {str(pg_version).split(',')[0] if pg_version else 'Unknown'}"
            )
            if timescale_version:
                section.append(f"- **TimescaleDB:** {timescale_version}")
            section.append(f"- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            return section
        except Exception:
            pass

        return []

    async def bulk_insert_market_data(
        self, data: List[Dict], table_name: str = "market_data_seconds"
    ) -> bool:
        """
        Bulk insert market data with validation and conflict handling

        Args:
            data: List of data dictionaries
            table_name: Target table name

        Returns:
            Success status
        """
        if not data:
            return True

        try:
            # Validate data structure
            if table_name in self.table_schemas:
                schema = self.table_schemas[table_name]
                for record in data:
                    missing_cols = [col for col in schema["required_columns"] if col not in record]
                    if missing_cols:
                        logger.error(f"Missing required columns for {table_name}: {missing_cols}")
                        return False

            async with get_async_session() as session:
                helper = TimescaleDBHelper(session)

                # Process data to handle pandas timestamps and NaN values
                processed_data = []
                for record in data:
                    processed_record = {}
                    for key, value in record.items():
                        if isinstance(value, pd.Timestamp):
                            processed_record[key] = value.to_pydatetime()
                        elif pd.isna(value) if hasattr(pd, "isna") else value is None:
                            processed_record[key] = None
                        else:
                            processed_record[key] = value
                    processed_data.append(processed_record)

                # Use bulk insert with conflict handling
                await helper.bulk_insert_market_data(processed_data, table_name)

                self._report_progress(f"Inserted {len(processed_data)} records to {table_name}")
                return True

        except Exception as e:
            error_msg = f"Error inserting data to {table_name}: {str(e)}"
            logger.error(error_msg)
            return False

    async def get_data_statistics(self, symbol: Optional[str] = None) -> Dict:
        """
        Get comprehensive data statistics

        Args:
            symbol: Optional symbol filter

        Returns:
            Dictionary with statistics
        """
        try:
            async with get_async_session() as session:
                stats = {
                    "total_records": {},
                    "symbol_breakdown": {},
                    "date_ranges": {},
                    "data_quality": {},
                }

                # Table record counts
                tables = [
                    "market_data_seconds",
                    "market_data_minutes",
                    "raw_tick_data",
                    "features",
                    "predictions",
                    "trades",
                ]

                for table in tables:
                    try:
                        if symbol:
                            result = await session.execute(
                                text(
                                    f"""
                                SELECT COUNT(*) FROM {table} WHERE symbol = :symbol
                            """
                                ),
                                {"symbol": symbol},
                            )
                        else:
                            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))

                        stats["total_records"][table] = result.scalar()
                    except Exception:
                        stats["total_records"][table] = 0

                # Symbol breakdown for main tables
                for table in ["market_data_seconds", "market_data_minutes"]:
                    try:
                        if symbol:
                            result = await session.execute(
                                text(
                                    f"""
                                SELECT exchange, COUNT(*) as count
                                FROM {table}
                                WHERE symbol = :symbol
                                GROUP BY exchange
                                ORDER BY count DESC
                            """
                                ),
                                {"symbol": symbol},
                            )
                        else:
                            result = await session.execute(
                                text(
                                    f"""
                                SELECT symbol, exchange, COUNT(*) as count
                                FROM {table}
                                GROUP BY symbol, exchange
                                ORDER BY count DESC
                                LIMIT 20
                            """
                                )
                            )

                        stats["symbol_breakdown"][table] = [
                            {
                                "symbol": row[0] if not symbol else symbol,
                                "exchange": row[1] if symbol else row[1],
                                "count": row[2] if symbol else row[2],
                            }
                            for row in result.fetchall()
                        ]
                    except Exception:
                        stats["symbol_breakdown"][table] = []
                # Date ranges
                for table in ["market_data_seconds", "market_data_minutes"]:
                    try:
                        if symbol:
                            result = await session.execute(
                                text(
                                    f"""
                                SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date
                                FROM {table}
                                WHERE symbol = :symbol
                            """
                                ),
                                {"symbol": symbol},
                            )
                        else:
                            result = await session.execute(
                                text(
                                    f"""
                                SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date
                                FROM {table}
                            """
                                )
                            )

                        row = result.fetchone()
                        if row:
                            stats["date_ranges"][table] = {
                                "min_date": row[0],
                                "max_date": row[1],
                                "days_span": ((row[1] - row[0]).days if row[0] and row[1] else 0),
                            }
                        else:
                            stats["date_ranges"][table] = {
                                "min_date": None,
                                "max_date": None,
                                "days_span": 0,
                            }
                    except Exception as e:
                        logger.warning(f"Error getting date ranges for {table}: {e}")
                        stats["date_ranges"][table] = {
                            "min_date": None,
                            "max_date": None,
                            "days_span": 0,
                            "error": str(e),
                        }

                return stats
        except Exception as e:
            logger.error(f"Error getting data statistics: {e}")
            return {
                "error": str(e),
                "total_records": {},
                "symbol_breakdown": {},
                "date_ranges": {},
                "data_quality": {},
            }

    async def get_connection_info(self) -> Dict:
        """
        Get detailed database connection information

        Returns:
            Dictionary with connection details
        """
        try:
            async with get_async_session() as session:
                info = {
                    "connected": True,
                    "server_info": {},
                    "database_info": {},
                    "extensions": [],
                    "settings": {},
                }

                # Server version and info
                result = await session.execute(text("SELECT version()"))
                info["server_info"]["version"] = result.scalar()

                result = await session.execute(text("SELECT current_database()"))
                info["database_info"]["name"] = result.scalar()

                result = await session.execute(text("SELECT current_user"))
                info["database_info"]["user"] = result.scalar()

                result = await session.execute(
                    text("SELECT inet_server_addr(), inet_server_port()")
                )
                server_info = result.fetchone()
                if server_info:
                    info["server_info"]["host"] = server_info[0]
                    info["server_info"]["port"] = server_info[1]

                # Extensions
                result = await session.execute(
                    text(
                        """
                    SELECT extname, extversion
                    FROM pg_extension
                    ORDER BY extname
                """
                    )
                )

                info["extensions"] = [
                    {"name": row[0], "version": row[1]} for row in result.fetchall()
                ]

                # Important settings
                settings_to_check = [
                    "shared_buffers",
                    "effective_cache_size",
                    "work_mem",
                    "maintenance_work_mem",
                    "max_connections",
                ]

                for setting in settings_to_check:
                    try:
                        result = await session.execute(text(f"SHOW {setting}"))
                        info["settings"][setting] = result.scalar()
                    except:
                        pass

                return info

        except Exception as e:
            return {"connected": False, "error": str(e)}
