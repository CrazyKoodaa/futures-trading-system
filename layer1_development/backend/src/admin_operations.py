"""
Admin Operations Module - Core Business Logic

This module contains the main AdminOperations class that coordinates all
business logic for the futures trading system admin tool.

Key Features:
- Async/await throughout for performance
- Comprehensive error handling and recovery
- Progress tracking with live callbacks
- Markdown-formatted responses for display
- Integration with database and Rithmic operations
"""

import asyncio
import logging
import re
import fnmatch
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass
import pandas as pd

# Local imports
from admin_core_classes import SystemStatus, DownloadProgress
from admin_database import get_async_session, TimescaleDBHelper

# Import the new modular Rithmic operations
from admin_rithmic_connection import RithmicConnectionManager
from admin_rithmic_symbols import RithmicSymbolManager
from admin_rithmic_historical import RithmicHistoricalManager
from admin_rithmic_operations import RithmicOperationsManager

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Container for symbol search results"""

    symbol: str
    product_code: str
    name: str
    instrument_type: str
    expiration_date: str
    exchange: str
    selected: bool = False


@dataclass
class ContractInfo:
    """Container for contract information"""

    symbol: str
    front_month: str
    exchange: str
    data_points: int = 0
    latest_data: Optional[str] = None


class AdminOperations:
    """
    Main business logic coordinator for the admin tool.

    This class orchestrates all operations between the database,
    Rithmic API, and user interface components.
    """

    # Quarterly month codes for NQ/ES futures
    QUARTERLY_MONTHS = ["H", "M", "U", "Z"]

    # Month code to number mapping
    MONTH_CODES = {
        "F": 1,
        "G": 2,
        "H": 3,
        "J": 4,
        "K": 5,
        "M": 6,
        "N": 7,
        "Q": 8,
        "U": 9,
        "V": 10,
        "X": 11,
        "Z": 12,
    }

    # Instrument specifications
    INSTRUMENT_SPECS = {
        "NQ": {
            "full_name": "E-mini NASDAQ 100",
            "tick_size": 0.25,
            "point_value": 20.0,
            "currency": "USD",
            "exchange": "CME",
            "exchange_code": "XCME",
            "months": ["H", "M", "U", "Z"],
            "trading_hours": "23:00-22:00",
        },
        "ES": {
            "full_name": "E-mini S&P 500",
            "tick_size": 0.25,
            "point_value": 50.0,
            "currency": "USD",
            "exchange": "CME",
            "exchange_code": "XCME",
            "months": ["H", "M", "U", "Z"],
            "trading_hours": "23:00-22:00",
        },
        "YM": {
            "full_name": "E-mini Dow Jones",
            "tick_size": 1.0,
            "point_value": 5.0,
            "currency": "USD",
            "exchange": "CBOT",
            "exchange_code": "XCBT",
            "months": ["H", "M", "U", "Z"],
            "trading_hours": "23:00-22:00",
        },
        "RTY": {
            "full_name": "E-mini Russell 2000",
            "tick_size": 0.10,
            "point_value": 50.0,
            "currency": "USD",
            "exchange": "CME",
            "exchange_code": "XCME",
            "months": ["H", "M", "U", "Z"],
            "trading_hours": "23:00-22:00",
        },
    }

    def __init__(
        self, status: SystemStatus, progress_callback: Callable[[str, float], None]
    ):
        """
        Initialize AdminOperations.

        Args:
            status: SystemStatus instance to track system state
            progress_callback: Function to call for progress updates
        """
        self.status = status
        self.progress_callback = progress_callback

        # Initialize Rithmic operation modules
        self.connection_manager = None  # RithmicConnectionManager
        self.symbol_ops = None  # RithmicSymbolManager
        self.historical_ops = None  # RithmicHistoricalManager
        self.rithmic_ops = None  # RithmicOperationsManager (main coordinator)
        self.db_ops = None  # DatabaseOperations

        # Initialize download progress tracking
        self.download_progress = {}

        # Add missing attributes
        self.historical_manager = None

        logger.info("AdminOperations initialized")

    def _report_progress(self, message: str, progress: float = 0.0):
        """Report progress to callback if available

        Args:
            message: Progress message
            progress: Progress value (unused in current implementation)
        """
        if self.progress_callback:
            self.progress_callback(message, progress)
        logger.info(message)

    def set_operations(
        self,
        db_ops,
        connection_manager: RithmicConnectionManager,
        symbol_ops: RithmicSymbolManager,
        historical_ops: RithmicHistoricalManager,
        rithmic_ops: RithmicOperationsManager,
    ):
        """Set database and Rithmic operations instances."""
        self.db_ops = db_ops
        self.connection_manager = connection_manager
        self.symbol_ops = symbol_ops
        self.historical_ops = historical_ops
        self.rithmic_ops = rithmic_ops
        logger.info("Database and Rithmic operations set")

    async def test_connections(self) -> str:
        """
        Test both database and Rithmic connections.

        Returns:
            Markdown-formatted status report
        """
        logger.info("Starting connection tests")

        result = "# Connection Test Results\n\n"

        try:
            # Test database connection
            self.progress_callback("Testing database connection...", 0.1)

            if self.db_ops:
                db_result = await self.db_ops.test_connection()
                if db_result:
                    self.status.db_connected = True
                    result += "✅ **Database**: Connected successfully\n"

                    # Test table access
                    table_result = await self.db_ops.verify_tables()
                    if table_result:
                        result += "✅ **Tables**: All required tables accessible\n"
                    else:
                        result += "⚠️ **Tables**: Some tables may be missing\n"
                else:
                    self.status.db_connected = False
                    result += "❌ **Database**: Connection failed\n"
            else:
                result += "❌ **Database**: Operations not initialized\n"

            self.progress_callback("Testing Rithmic connection...", 0.5)

            # Test Rithmic connection
            if self.connection_manager:
                rithmic_result = await self.connection_manager.test_connection()
                if rithmic_result:
                    self.status.rithmic_connected = True
                    result += "✅ **Rithmic**: Connected successfully\n"
                    result += f"   - Gateway: {self.status.rithmic_gateway}\n"
                    result += f"   - User: {self.status.rithmic_user}\n"
                else:
                    self.status.rithmic_connected = False
                    result += "❌ **Rithmic**: Connection failed\n"
            else:
                result += "❌ **Rithmic**: Operations not initialized\n"

            self.progress_callback("Connection tests completed", 1.0)

            # Summary
            result += "\n## Summary\n\n"
            if self.status.db_connected and self.status.rithmic_connected:
                result += "🎉 **All systems ready!** Ready for data operations.\n"
            elif self.status.db_connected or self.status.rithmic_connected:
                result += (
                    "⚠️ **Partial connectivity** - Some operations may be limited.\n"
                )
            else:
                result += "❌ **No connectivity** - Please check configuration.\n"

        except Exception as e:
            logger.error(f"Error during connection tests: {e}")
            result += f"\n❌ **Error**: {str(e)}\n"
            self.progress_callback("Connection test failed", 0.0)

        return result

    async def search_and_check_symbols(
        self, search_term: str = "", exchange: str = "CME"
    ) -> str:
        """
        Search for symbols and check their contracts.

        Args:
            search_term: Search pattern (supports wildcards * and ?)
            exchange: Exchange to search on

        Returns:
            Markdown-formatted search results
        """
        logger.info(f"Searching symbols: '{search_term}' on {exchange}")

        if not self.status.rithmic_connected:
            return "❌ **Error**: Not connected to Rithmic. Please test connections first.\n"

        result = f"# Symbol Search Results\n\n**Search Term**: `{search_term}`\n**Exchange**: {exchange}\n\n"

        try:
            self.progress_callback("Searching symbols...", 0.1)

            # Handle wildcards
            has_wildcards = "*" in search_term or "?" in search_term
            search_term_for_api = search_term

            if has_wildcards:
                # Extract base term for API search
                search_term_for_api = re.split(r"[\*\?]", search_term)[0]
                if not search_term_for_api:
                    search_term_for_api = search_term.replace("*", "").replace("?", "")
                    if not search_term_for_api:
                        search_term_for_api = "A"

            # Search symbols via Rithmic
            raw_results = await self.symbol_ops.search_symbols(
                search_term_for_api, exchange=exchange
            )

            if not raw_results:
                return (
                    result
                    + f"No symbols found matching '{search_term}' on {exchange}\n"
                )

            self.progress_callback("Filtering results...", 0.3)

            # Filter results
            filtered_results = []
            if has_wildcards:
                pattern = search_term.replace("?", ".").replace("*", ".*")
                quarterly_contracts_only = search_term.upper().startswith(("NQ", "ES"))

                for raw_result in raw_results:
                    symbol = raw_result.get("symbol", "")

                    # Special filtering for NQ/ES quarterly contracts
                    if quarterly_contracts_only:
                        month_code = self._extract_month_code(symbol)
                        if month_code and month_code not in self.QUARTERLY_MONTHS:
                            continue

                    # Apply wildcard pattern
                    if re.match(pattern, symbol, re.IGNORECASE) or re.match(
                        pattern, raw_result.get("product_code", ""), re.IGNORECASE
                    ):
                        filtered_results.append(raw_result)
            else:
                filtered_results = raw_results

            if not filtered_results:
                return result + f"No symbols found matching pattern '{search_term}'\n"

            self.progress_callback("Processing results...", 0.5)

            # Convert to SearchResult objects
            search_results = []
            for raw_result in filtered_results:
                search_result = SearchResult(
                    symbol=raw_result.get("symbol", ""),
                    product_code=raw_result.get("product_code", ""),
                    name=raw_result.get("symbol_name", ""),
                    instrument_type=raw_result.get("instrument_type", ""),
                    expiration_date=str(raw_result.get("expiration_date", "")),
                    exchange=raw_result.get("exchange", exchange),
                )
                search_results.append(search_result)

            # Simulate interactive selection (for now, select first few)
            selected_results = await self._simulate_interactive_selection(
                search_results
            )

            self.progress_callback("Checking contracts...", 0.7)

            # Update status with selected symbols
            self.status.current_symbols = [r.symbol for r in selected_results]
            self.status.current_exchange = exchange

            # Check contracts and database data
            available_contracts = {}
            for search_result in selected_results:
                symbol = search_result.symbol

                # Get front month contract
                front_month = await self.symbol_ops.get_front_month_contract(
                    search_result.product_code, exchange
                )

                # Check database data
                db_info = {}
                if self.status.db_connected:
                    db_info = await self._check_database_data(symbol, exchange)

                available_contracts[symbol] = ContractInfo(
                    symbol=symbol,
                    front_month=front_month or "Unknown",
                    exchange=exchange,
                    data_points=db_info.get("total_points", 0),
                    latest_data=db_info.get("latest_timestamp"),
                )

            self.status.available_contracts = available_contracts

            self.progress_callback("Search completed", 1.0)

            # Format results
            result += f"## Found {len(selected_results)} Symbols\n\n"

            for search_result in selected_results:
                symbol = search_result.symbol
                month_info = self._get_month_info(symbol)

                result += f"### {symbol}\n"
                result += f"- **Product**: {search_result.product_code}\n"
                result += f"- **Name**: {search_result.name}\n"
                result += f"- **Expiration**: {search_result.expiration_date}\n"
                if month_info:
                    result += f"- **Month**: {month_info}\n"

                # Contract info
                if symbol in available_contracts:
                    info = available_contracts[symbol]
                    result += f"- **Front Month**: {info.front_month}\n"
                    result += f"- **Data Points**: {info.data_points:,}\n"
                    if info.latest_data:
                        result += f"- **Latest Data**: {info.latest_data}\n"

                result += "\n"

            result += f"✅ **Search completed** - {len(selected_results)} symbols ready for operations\n"

        except Exception as e:
            logger.error(f"Error in symbol search: {e}")
            result += f"\n❌ **Error**: {str(e)}\n"
            self.progress_callback("Search failed", 0.0)

        return result

    async def download_historical_data(
        self,
        days: int = 7,
        download_seconds: bool = True,
        download_minutes: bool = False,
    ) -> str:
        """
        Download historical data for selected symbols.

        Args:
            days: Number of days to download
            download_seconds: Whether to download second bars
            download_minutes: Whether to download minute bars

        Returns:
            Markdown-formatted download report
        """
        logger.info(f"Starting historical data download: {days} days")

        if not self.status.rithmic_connected:
            return "❌ **Error**: Not connected to Rithmic. Please test connections first.\n"

        if not self.status.db_connected:
            return "❌ **Error**: Not connected to database. Please test connections first.\n"

        if not self.status.available_contracts:
            return (
                "❌ **Error**: No contracts available. Please search symbols first.\n"
            )

        result = f"# Historical Data Download\n\n"
        result += f"**Days**: {days}\n"
        result += f"**Types**: {'Second bars' if download_seconds else ''}"
        result += f"{' and ' if download_seconds and download_minutes else ''}"
        result += f"{'Minute bars' if download_minutes else ''}\n\n"

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        result += f"**Period**: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}\n\n"

        # Initialize progress tracking
        total_operations = len(self.status.available_contracts) * (
            int(download_seconds) + int(download_minutes)
        )
        current_operation = 0

        self.download_progress = {
            symbol: DownloadProgress()
            for symbol in self.status.available_contracts.keys()
        }

        try:
            async with get_async_session() as session:
                helper = TimescaleDBHelper(session)

                for symbol, contract_info in self.status.available_contracts.items():
                    result += f"## Processing {symbol}\n\n"

                    # Download second bars
                    if download_seconds:
                        current_operation += 1
                        progress = current_operation / total_operations
                        self.progress_callback(
                            f"Downloading second bars for {symbol}...", progress
                        )

                        second_result = await self._download_second_bars(
                            symbol, contract_info.exchange, days
                        )
                        result += f"Downloaded {second_result.get('records', 0)} second bars for {symbol}\n"

                    # Download minute bars
                    if download_minutes:
                        current_operation += 1
                        progress = current_operation / total_operations
                        self.progress_callback(
                            f"Downloading minute bars for {symbol}...", progress
                        )

                        minute_result = await self._download_minute_bars(
                            symbol, contract_info.exchange, days
                        )
                        result += f"Downloaded {minute_result.get('records', 0)} minute bars for {symbol}\n"

            self.progress_callback("Download completed", 1.0)

            # Summary
            result += "## Download Summary\n\n"
            total_records = 0
            for symbol, progress in self.download_progress.items():
                result += f"- **{symbol}**: {progress.records_downloaded:,} records\n"
                total_records += progress.records_downloaded

            result += f"\n✅ **Total downloaded**: {total_records:,} records\n"

        except Exception as e:
            logger.error(f"Error during download: {e}")
            result += f"\n❌ **Error**: {str(e)}\n"
            self.progress_callback("Download failed", 0.0)

        return result

    async def view_database_data(self) -> str:
        """
        View database contents and statistics.

        Returns:
            Markdown-formatted database overview
        """
        if not self.status.db_connected:
            return "❌ **Error**: Not connected to database. Please test connections first.\n"

        result = "# Database Contents\n\n"

        try:
            self.progress_callback("Querying database...", 0.5)

            async with get_async_session() as session:
                from sqlalchemy import text

                # Table summary
                result += "## Table Summary\n\n"

                # Count records in each table
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
                        count_result = await session.execute(
                            text(f"SELECT COUNT(*) FROM {table}")
                        )
                        count = count_result.scalar()
                        result += f"- **{table}**: {count:,} records\n"
                    except Exception as e:
                        result += f"- **{table}**: Error ({str(e)})\n"

                # Symbol breakdown
                result += "\n## Available Symbols\n\n"

                try:
                    symbols_result = await session.execute(
                        text(
                            """
                        SELECT symbol, exchange, COUNT(*) as count,
                               MIN(timestamp) as first_data,
                               MAX(timestamp) as last_data
                        FROM market_data_seconds
                        GROUP BY symbol, exchange
                        ORDER BY symbol, exchange
                    """
                        )
                    )
                    symbols_data = symbols_result.fetchall()

                    if symbols_data:
                        for row in symbols_data:
                            result += f"### {row[0]} ({row[1]})\n"
                            result += f"- **Records**: {row[2]:,}\n"
                            result += f"- **Period**: {row[3]} to {row[4]}\n\n"
                    else:
                        result += "No data found in market_data_seconds table\n\n"

                except Exception as e:
                    result += f"Error querying symbols: {str(e)}\n\n"

                # Recent data sample
                result += "## Recent Data Sample\n\n"

                try:
                    recent_result = await session.execute(
                        text(
                            """
                        SELECT timestamp, symbol, contract, exchange,
                               open, high, low, close, volume
                        FROM market_data_seconds
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """
                        )
                    )
                    recent_data = recent_result.fetchall()

                    if recent_data:
                        result += "| Time | Symbol | Contract | OHLC | Volume |\n"
                        result += "|------|--------|----------|------|--------|\n"

                        for row in recent_data:
                            ohlc = (
                                f"{row[4]:.2f}/{row[5]:.2f}/{row[6]:.2f}/{row[7]:.2f}"
                            )
                            result += f"| {row[0]} | {row[1]} | {row[2]} | {ohlc} | {row[8]} |\n"
                    else:
                        result += "No recent data available\n"

                except Exception as e:
                    result += f"Error querying recent data: {str(e)}\n"

            self.progress_callback("Database query completed", 1.0)

        except Exception as e:
            logger.error(f"Error viewing database data: {e}")
            result += f"\n❌ **Error**: {str(e)}\n"
            self.progress_callback("Database query failed", 0.0)

        return result

    def _extract_month_code(self, symbol: str) -> str:
        """
        Extract the month code from a futures symbol

        Args:
            symbol: The futures symbol (e.g., 'ESZ23', 'NQH24')

        Returns:
            The month code (e.g., 'Z', 'H')
        """
        if not symbol or len(symbol) < 3:
            return ""

        # Standard format is like ESZ23, NQH24, etc.
        # The month code is typically the character before the year
        # Find the position of the first digit which should be the year
        for i, char in enumerate(symbol):
            if char.isdigit():
                if i > 0:
                    return symbol[i - 1]
                break

        return ""

    def _get_month_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get information about the contract month from a futures symbol

        Args:
            symbol: The futures symbol (e.g., 'ESZ23', 'NQH24')

        Returns:
            Dictionary with month information
        """
        month_code = self._extract_month_code(symbol)

        # Standard CME month codes
        month_codes = {
            "F": {"month": 1, "name": "January"},
            "G": {"month": 2, "name": "February"},
            "H": {"month": 3, "name": "March"},
            "J": {"month": 4, "name": "April"},
            "K": {"month": 5, "name": "May"},
            "M": {"month": 6, "name": "June"},
            "N": {"month": 7, "name": "July"},
            "Q": {"month": 8, "name": "August"},
            "U": {"month": 9, "name": "September"},
            "V": {"month": 10, "name": "October"},
            "X": {"month": 11, "name": "November"},
            "Z": {"month": 12, "name": "December"},
        }

        if month_code in month_codes:
            return month_codes[month_code]
        else:
            return {"month": 0, "name": "Unknown"}

    async def _simulate_interactive_selection(
        self, search_results: List[Dict]
    ) -> List[Dict]:
        """
        Simulate an interactive selection of search results

        In a real TUI application, this would show a selection UI.
        For this implementation, we'll just select all results.

        Args:
            search_results: List of search result dictionaries

        Returns:
            List of selected results
        """
        # In a real application, this would show a UI for selection
        # For now, we'll just return all results (auto-select all)
        return search_results

    async def _check_database_data(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """
        Check if data for a symbol already exists in the database

        Args:
            symbol: The symbol to check
            exchange: The exchange for the symbol (unused in current implementation)

        Returns:
            Dictionary with database information
        """
        if not self.db_ops:
            return {
                "exists": False,
                "seconds_data": 0,
                "minutes_data": 0,
                "first_date": None,
                "last_date": None,
            }

        try:
            # Get table info for seconds data
            seconds_info = await self.db_ops.get_table_info("market_data_seconds")
            minutes_info = await self.db_ops.get_table_info("market_data_minutes")

            # Check if tables exist
            if not seconds_info.get("exists", False) or not minutes_info.get(
                "exists", False
            ):
                return {
                    "exists": False,
                    "seconds_data": 0,
                    "minutes_data": 0,
                    "first_date": None,
                    "last_date": None,
                }

            # Get data statistics
            stats = await self.db_ops.get_data_statistics(symbol)

            # Extract relevant information
            seconds_count = stats.get("total_records", {}).get("market_data_seconds", 0)
            minutes_count = stats.get("total_records", {}).get("market_data_minutes", 0)

            # Get date ranges
            seconds_range = stats.get("date_ranges", {}).get("market_data_seconds", {})
            first_date = seconds_range.get("first_data")
            last_date = seconds_range.get("last_data")

            return {
                "exists": seconds_count > 0 or minutes_count > 0,
                "seconds_data": seconds_count,
                "minutes_data": minutes_count,
                "first_date": first_date,
                "last_date": last_date,
            }

        except Exception as e:
            logger.error(f"Error checking database data: {e}")
            return {
                "exists": False,
                "seconds_data": 0,
                "minutes_data": 0,
                "first_date": None,
                "last_date": None,
                "error": str(e),
            }

    async def _download_second_bars(
        self, symbol: str, exchange: str, days: int
    ) -> Dict[str, Any]:
        """
        Download second-level bar data for a symbol

        Args:
            symbol: The symbol to download data for
            exchange: The exchange for the symbol
            days: Number of days to download

        Returns:
            Dictionary with download results
        """
        if not self.connection_manager or not self.historical_manager:
            return {"success": False, "error": "Connection managers not initialized"}

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Format dates for the historical manager
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            # Request historical data
            self._report_progress(
                f"Downloading {days} days of second bars for {symbol}...", 0.4
            )

            # Call the historical manager to get the data
            data = await self.historical_manager.get_historical_data(
                symbol=symbol,
                exchange=exchange,
                start_date=start_str,
                end_date=end_str,
                bar_type="second",
            )

            if not data or "error" in data:
                return {
                    "success": False,
                    "error": data.get("error", "Unknown error"),
                    "records": 0,
                }

            # Insert data into database
            if self.db_ops and "bars" in data and data["bars"]:
                self._report_progress(
                    f"Inserting {len(data['bars'])} second bars into database...", 0.6
                )

                # Convert to database format
                db_records = []
                for bar in data["bars"]:
                    db_records.append(
                        {
                            "symbol": symbol,
                            "exchange": exchange,
                            "timestamp": bar.get("timestamp"),
                            "open": bar.get("open"),
                            "high": bar.get("high"),
                            "low": bar.get("low"),
                            "close": bar.get("close"),
                            "volume": bar.get("volume", 0),
                            "tick_count": bar.get("tick_count", 0),
                        }
                    )

                # Validate and insert data
                valid, errors = await self.db_ops.validate_data_before_insert(
                    db_records, "market_data_seconds"
                )

                if not valid:
                    return {
                        "success": False,
                        "error": f"Data validation failed: {errors[:3]}...",
                        "records": 0,
                    }

                # Insert the data
                insert_success = await self.db_ops.bulk_insert_market_data(
                    db_records, "market_data_seconds"
                )

                if insert_success:
                    return {
                        "success": True,
                        "records": len(db_records),
                        "start_date": start_str,
                        "end_date": end_str,
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to insert data into database",
                        "records": 0,
                    }

            return {
                "success": True,
                "records": len(data.get("bars", [])),
                "start_date": start_str,
                "end_date": end_str,
                "note": "Data retrieved but not inserted into database",
            }

        except Exception as e:
            logger.error(f"Error downloading second bars: {e}")
            return {"success": False, "error": str(e), "records": 0}

    async def _download_minute_bars(
        self, symbol: str, exchange: str, days: int
    ) -> Dict[str, Any]:
        """
        Download minute-level bar data for a symbol

        Args:
            symbol: The symbol to download data for
            exchange: The exchange for the symbol
            days: Number of days to download

        Returns:
            Dictionary with download results
        """
        if not self.connection_manager or not self.historical_manager:
            return {"success": False, "error": "Connection managers not initialized"}

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Format dates for the historical manager
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            # Request historical data
            self._report_progress(
                f"Downloading {days} days of minute bars for {symbol}...", 0.7
            )

            # Call the historical manager to get the data
            data = await self.historical_manager.get_historical_data(
                symbol=symbol,
                exchange=exchange,
                start_date=start_str,
                end_date=end_str,
                bar_type="minute",
            )

            if not data or "error" in data:
                return {
                    "success": False,
                    "error": data.get("error", "Unknown error"),
                    "records": 0,
                }

            # Insert data into database
            if self.db_ops and "bars" in data and data["bars"]:
                self._report_progress(
                    f"Inserting {len(data['bars'])} minute bars into database...", 0.9
                )

                # Convert to database format
                db_records = []
                for bar in data["bars"]:
                    db_records.append(
                        {
                            "symbol": symbol,
                            "exchange": exchange,
                            "timestamp": bar.get("timestamp"),
                            "open": bar.get("open"),
                            "high": bar.get("high"),
                            "low": bar.get("low"),
                            "close": bar.get("close"),
                            "volume": bar.get("volume", 0),
                            "tick_count": bar.get("tick_count", 0),
                        }
                    )

                # Validate and insert data
                valid, errors = await self.db_ops.validate_data_before_insert(
                    db_records, "market_data_minutes"
                )

                if not valid:
                    return {
                        "success": False,
                        "error": f"Data validation failed: {errors[:3]}...",
                        "records": 0,
                    }

                # Insert the data
                insert_success = await self.db_ops.bulk_insert_market_data(
                    db_records, "market_data_minutes"
                )

                if insert_success:
                    return {
                        "success": True,
                        "records": len(db_records),
                        "start_date": start_str,
                        "end_date": end_str,
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to insert data into database",
                        "records": 0,
                    }

            return {
                "success": True,
                "records": len(data.get("bars", [])),
                "start_date": start_str,
                "end_date": end_str,
                "note": "Data retrieved but not inserted into database",
            }

        except Exception as e:
            logger.error(f"Error downloading minute bars: {e}")
            return {"success": False, "error": str(e), "records": 0}

    async def initialize_database(self) -> str:
        """
        Initialize the database with required tables and extensions.

        Returns:
            Markdown-formatted initialization report
        """
        result = "# Database Initialization Report\n\n"

        if not self.db_ops:
            return (
                result
                + "❌ **Error**: Database operations manager not initialized.\n\nPlease check your database configuration and try again."
            )

        self._report_progress("Initializing database...", 0.1)

        try:
            # Initialize the database
            success, message = await self.db_ops.initialize_database()

            if success:
                self._report_progress("Database initialized successfully", 1.0)
                result += "## ✅ Success\n\n"
                result += f"{message}\n\n"

                # Get database summary
                self._report_progress("Getting database summary...", 0.9)
                summary = await self.db_ops.get_database_summary()

                result += "## Database Summary\n\n"
                result += summary

                # Add connection info
                connection_info = await self.db_ops.get_connection_info()
                if connection_info and connection_info.get("connected", False):
                    result += "\n\n## Connection Information\n\n"
                    result += f"- **Server**: {connection_info.get('server_info', {}).get('version', 'Unknown')}\n"
                    result += f"- **Database**: {connection_info.get('database_info', {}).get('name', 'Unknown')}\n"
                    result += f"- **User**: {connection_info.get('database_info', {}).get('user', 'Unknown')}\n"
                    result += f"- **Size**: {connection_info.get('database_info', {}).get('size', 'Unknown')}\n"

                    # Add TimescaleDB info if available
                    if "timescaledb_version" in connection_info.get("server_info", {}):
                        result += f"- **TimescaleDB Version**: {connection_info['server_info']['timescaledb_version']}\n"

                    # Add hypertables info
                    hypertables = connection_info.get("database_info", {}).get(
                        "hypertables", []
                    )
                    if hypertables:
                        result += "\n### Hypertables\n\n"
                        for ht in hypertables:
                            result += f"- **{ht.get('name', 'Unknown')}**: {ht.get('chunks', 0)} chunks\n"
            else:
                self._report_progress("Database initialization failed", 0.0)
                result += "## ❌ Error\n\n"
                result += f"{message}\n\n"
                result += "Please check the logs for more details."

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            self._report_progress("Database initialization failed", 0.0)
            result += "## ❌ Error\n\n"
            result += f"An unexpected error occurred: {str(e)}\n\n"
            result += "Please check the logs for more details."

        return result
