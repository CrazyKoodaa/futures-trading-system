#!/usr/bin/env python3
"""
Rithmic Operations Coordinator

This module provides the main coordinator class for all Rithmic operations,
orchestrating connection management, symbol operations, and historical data downloads.

Key Features:
- High-level operation orchestration
- Cross-module dependency management
- Database integration coordination
- Comprehensive error handling
- Progress tracking across all operations
- Markdown-formatted results for display

Author: Trading System Admin Tool
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Any, Callable, Optional
from datetime import datetime, timedelta

# Import Rithmic manager modules
from admin_rithmic_connection import RithmicConnectionManager
from admin_rithmic_symbols import RithmicSymbolManager
from admin_rithmic_historical import RithmicHistoricalManager

# Configure logging
logger = logging.getLogger(__name__)


class RithmicOperationsManager:
    """
    Main coordinator class for all Rithmic operations.

    This class orchestrates all Rithmic-related functionality through
    specialized managers, providing a clean high-level interface for
    the main business logic.
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize the Rithmic operations coordinator.

        Args:
            progress_callback: Optional callback for progress updates
        """
        self.progress_callback = progress_callback
        self.database_ops = None  # Injected later

        # Initialize all Rithmic managers
        logger.info("Initializing Rithmic operations coordinator")

        # Create a no-op callback if none provided
        def noop_callback(*args, **kwargs):
            pass
        
        self.connection_manager = RithmicConnectionManager(progress_callback if callable(progress_callback) else noop_callback)
        self.symbol_manager = RithmicSymbolManager(
            self.connection_manager, progress_callback if callable(progress_callback) else noop_callback
        )
        self.historical_manager = RithmicHistoricalManager(
            self.connection_manager,
            None,  # database_ops injected later
            progress_callback if callable(progress_callback) else None,
        )

        logger.info("Rithmic operations coordinator initialized successfully")

    def set_database_operations(self, database_ops):
        """
        Set database operations for integration with data storage.

        Args:
            database_ops: Database operations instance
        """
        self.database_ops = database_ops
        self.historical_manager.database_ops = database_ops
        logger.info("Database operations configured for Rithmic coordinator")

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test Rithmic connection with comprehensive validation.

        Returns:
            Tuple of (success, message)
        """
        logger.info("Testing Rithmic connection")

        try:
            # Test connection through connection manager
            success, message = await self.connection_manager.test_connection()

            if success:
                logger.info("Rithmic connection test successful")
                return True, f"✅ **Connection Successful**\n{message}"
            else:
                logger.warning(f"Rithmic connection test failed: {message}")
                return False, f"❌ **Connection Failed**\n{message}"

        except Exception as e:
            logger.error(f"Exception during connection test: {e}")
            return False, f"❌ **Connection Test Error**\n{str(e)}"

    async def search_and_check_symbols(
        self, search_term: str, exchange: str = "CME"
    ) -> str:
        """
        Complete symbol search workflow with database verification.

        This method orchestrates the entire symbol search process:
        1. Ensures Rithmic connection
        2. Searches for symbols with wildcards
        3. Simulates contract selection
        4. Verifies contracts against database
        5. Returns formatted results

        Args:
            search_term: Symbol search pattern (e.g., "ES", "NQ")
            exchange: Target exchange (default: "CME")

        Returns:
            Markdown formatted search results
        """
        logger.info(
            f"Starting symbol search and check for '{search_term}' on {exchange}"
        )

        try:
            # 1. Ensure connection
            if not self.connection_manager.is_connected:
                self._update_progress("Connecting to Rithmic...")
                connected, msg = await self.connection_manager.connect()
                if not connected:
                    logger.error(f"Connection failed during symbol search: {msg}")
                    return f"❌ **Connection Failed**\n{msg}"

            # 2. Search symbols with wildcards
            self._update_progress(f"Searching for '{search_term}' symbols...")
            results = await self.symbol_manager.search_symbols(search_term, exchange)

            if not results:
                logger.warning(f"No symbols found for '{search_term}' on {exchange}")
                return f"❌ **No symbols found** matching '{search_term}' on {exchange}"

            logger.info(f"Found {len(results)} symbols for '{search_term}'")

            # 3. Interactive selection (simulated for TUI)
            self._update_progress("Selecting relevant contracts...")
            selected_contracts = await self.simulate_contract_selection(results)

            # 4. Verify contracts and check database
            if selected_contracts:
                self._update_progress("Verifying contracts with database...")
                verification_results = await self.verify_contracts_with_database(
                    selected_contracts
                )
            else:
                verification_results = {}

            # 5. Return formatted results
            self._update_progress("Formatting results...")
            formatted_results = self.format_symbol_search_results(
                results, verification_results
            )

            logger.info(f"Symbol search and check completed for '{search_term}'")
            return formatted_results

        except Exception as e:
            logger.error(f"Error during symbol search and check: {e}")
            return f"❌ **Symbol Search Error**\n{str(e)}"

    async def simulate_contract_selection(
        self, search_results: List[Dict]
    ) -> List[str]:
        """
        Simulate interactive contract selection for TUI.

        This method applies intelligent filtering to select the most
        relevant contracts automatically.

        Args:
            search_results: List of symbol search results

        Returns:
            List of selected contract symbols
        """
        logger.info(f"Simulating contract selection from {len(search_results)} results")

        try:
            # Filter to most relevant contracts
            filtered = self.symbol_manager.filter_quarterly_contracts(search_results)
            logger.info(f"Filtered to {len(filtered)} quarterly contracts")

            # Auto-select based on criteria:
            # - Current and next quarter contracts
            # - Active contracts only
            # - Limit to reasonable number (e.g., 4 contracts max)

            selected = []
            current_date = datetime.now()

            # Sort by expiration date and select most relevant
            sorted_contracts = sorted(
                filtered, key=lambda x: x.get("expiration_date", "")
            )

            for result in sorted_contracts[:4]:  # Limit selection to 4 contracts
                symbol = result.get("symbol", "")
                if symbol and symbol not in selected:
                    selected.append(symbol)
                    logger.debug(f"Selected contract: {symbol}")

            logger.info(f"Selected {len(selected)} contracts for verification")
            return selected

        except Exception as e:
            logger.error(f"Error during contract selection simulation: {e}")
            return []

    async def verify_contracts_with_database(
        self, contracts: List[str]
    ) -> Dict[str, Dict]:
        """
        Check database for existing data on contracts.

        Args:
            contracts: List of contract symbols to verify

        Returns:
            Dictionary mapping contract symbols to their database statistics
        """
        logger.info(f"Verifying {len(contracts)} contracts with database")

        if not hasattr(self, "database_ops") or not self.database_ops:
            logger.warning(
                "Database operations not available for contract verification"
            )
            return {}

        verification_results = {}

        for contract in contracts:
            try:
                # Get data statistics from database
                stats = await self.database_ops.get_data_statistics(contract)
                verification_results[contract] = stats
                logger.debug(f"Retrieved database stats for {contract}")

            except Exception as e:
                logger.warning(f"Error verifying contract {contract}: {e}")
                verification_results[contract] = {"error": str(e)}

        logger.info(f"Verified {len(verification_results)} contracts with database")
        return verification_results

    def format_symbol_search_results(
        self, search_results: List[Dict], db_verification: Dict[str, Dict]
    ) -> str:
        """
        Format search results with database info as markdown.

        Args:
            search_results: Raw search results from symbol manager
            db_verification: Database verification results

        Returns:
            Markdown formatted results string
        """
        logger.info("Formatting symbol search results")

        markdown_result = f"## 🔍 Symbol Search Results\n"
        markdown_result += f"Found **{len(search_results)}** contracts:\n"

        for result in search_results:
            symbol = result.get("symbol", "Unknown")
            markdown_result += f"### {symbol}\n"
            markdown_result += f"- **Exchange**: {result.get('exchange', 'Unknown')}\n"
            markdown_result += (
                f"- **Product**: {result.get('product_code', 'Unknown')}\n"
            )
            markdown_result += (
                f"- **Expiration**: {result.get('expiration_date', 'Unknown')}\n"
            )

            # Add trading hours if available
            if "trading_hours" in result:
                markdown_result += f"- **Trading Hours**: {result['trading_hours']}\n"

            # Add database info if available
            if symbol in db_verification:
                db_info = db_verification[symbol]
                if db_info is not None and "error" not in db_info:
                    markdown_result += (
                        f"- **Database Records**: {db_info.get('total_records', 0):,}\n"
                    )
                    if "latest_data" in db_info:
                        markdown_result += (
                            f"- **Latest Data**: {db_info['latest_data']}\n"
                        )
                    if "date_range" in db_info and db_info.get("date_range") is not None:
                        date_range = db_info["date_range"]
                        if date_range is not None:
                            markdown_result += f"- **Data Range**: {date_range.get('start', 'Unknown')} to {date_range.get('end', 'Unknown')}\n"
                else:
                    markdown_result += f"- **Database Status**: ⚠️ {db_info['error']}\n"
            else:
                markdown_result += f"- **Database Status**: No data found\n"

            markdown_result += "\n"

        # Add summary statistics
        total_db_records = sum(
            db_info.get("total_records", 0)
            for db_info in db_verification.values()
            if "error" not in db_info
        )

        if total_db_records > 0:
            markdown_result += (
                f"---\n**Total Database Records**: {total_db_records:,}\n"
            )

        logger.info("Symbol search results formatted successfully")
        return markdown_result

    async def download_historical_data(
        self, contracts: List[str], days: int = 7
    ) -> str:
        """
        Coordinate full historical data download process.

        This method orchestrates the complete download workflow:
        1. Validates prerequisites
        2. Configures historical manager
        3. Executes download with progress tracking
        4. Returns formatted results

        Args:
            contracts: List of contract symbols to download
            days: Number of historical days to download

        Returns:
            Formatted download results
        """
        logger.info(
            f"Starting historical data download for {len(contracts)} contracts, {days} days"
        )

        try:
            # Validate prerequisites
            self._update_progress("Validating download prerequisites...")
            prerequisites_check = await self.validate_download_prerequisites(contracts)

            if not prerequisites_check["valid"]:
                logger.error(
                    f"Prerequisites validation failed: {prerequisites_check['message']}"
                )
                return prerequisites_check["message"]

            # Set database operations for historical manager
            if hasattr(self, "database_ops") and self.database_ops:
                self.historical_manager.database_ops = self.database_ops
                logger.info("Database operations configured for historical manager")

            # Execute download with progress tracking
            self._update_progress(
                f"Downloading {days} days of data for {len(contracts)} contracts..."
            )

            result = await self.historical_manager.download_historical_data(
                contracts, days, download_seconds=True, download_minutes=True
            )

            logger.info("Historical data download completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error during historical data download: {e}")
            return f"❌ **Download Failed**\n{str(e)}"

    async def validate_download_prerequisites(
        self, contracts: List[str]
    ) -> Dict[str, Any]:
        """
        Validate all prerequisites for download operation.

        Args:
            contracts: List of contracts to validate

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating download prerequisites")

        # Check Rithmic connection
        if not self.connection_manager.is_connected:
            logger.info("Rithmic not connected, attempting connection...")
            connected, msg = await self.connection_manager.connect()
            if not connected:
                logger.error(f"Rithmic connection failed: {msg}")
                return {
                    "valid": False,
                    "message": f"❌ **Rithmic Connection Failed**\n{msg}",
                }

        # Check database availability
        if not hasattr(self, "database_ops") or not self.database_ops:
            logger.error("Database operations not available")
            return {
                "valid": False,
                "message": "❌ **Database Operations Not Available**\nDatabase connection required for historical downloads.",
            }

        # Validate contracts
        if not contracts:
            logger.error("No contracts provided for validation")
            return {
                "valid": False,
                "message": "❌ **No Contracts Selected**\nPlease select contracts to download.",
            }

        # Validate each contract format
        invalid_contracts = []
        for contract in contracts:
            if not contract or not isinstance(contract, str) or len(contract) < 2:
                invalid_contracts.append(contract)

        if invalid_contracts:
            logger.error(f"Invalid contracts found: {invalid_contracts}")
            return {
                "valid": False,
                "message": f"❌ **Invalid Contracts**\nInvalid contract formats: {', '.join(map(str, invalid_contracts))}",
            }

        logger.info("All download prerequisites validated successfully")
        return {"valid": True, "message": "All prerequisites met"}

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status across all Rithmic components.

        Returns:
            Dictionary with detailed status information
        """
        logger.info("Getting comprehensive system status")

        status = {
            "timestamp": datetime.now().isoformat(),
            "connection": {
                "connected": self.connection_manager.is_connected,
                "status": (
                    "Connected"
                    if self.connection_manager.is_connected
                    else "Disconnected"
                ),
            },
            "database": {
                "available": hasattr(self, "database_ops")
                and self.database_ops is not None
            },
            "managers": {
                "connection_manager": "Initialized",
                "symbol_manager": "Initialized",
                "historical_manager": "Initialized",
            },
        }

        # Add connection details if connected
        if self.connection_manager.is_connected:
            try:
                conn_info = await self.connection_manager.get_connection_info()
                status["connection"].update(conn_info)
            except Exception as e:
                status["connection"]["error"] = str(e)

        logger.info("System status retrieved successfully")
        return status

    def _update_progress(self, message: str, progress: Optional[float] = None):
        """
        Update progress through callback if available.

        Args:
            message: Progress message
            progress: Optional progress percentage (0-100)
        """
        if self.progress_callback is not None and callable(self.progress_callback):
            try:
                if progress is not None:
                    self.progress_callback(message, progress)
                else:
                    self.progress_callback(message)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")

    async def cleanup(self):
        """
        Clean up all Rithmic resources.

        This method performs best-effort cleanup of all managers
        and connections, logging but not raising exceptions.
        """
        logger.info("Starting Rithmic operations cleanup")

        cleanup_results = []

        # Cleanup historical manager
        try:
            if hasattr(self.historical_manager, "cleanup") and callable(getattr(self.historical_manager, "cleanup", None)):
                await self.historical_manager.cleanup()
                cleanup_results.append("Historical manager cleaned up")
            else:
                cleanup_results.append("Historical manager cleanup not available")
        except Exception as e:
            logger.warning(f"Error cleaning up historical manager: {e}")
            cleanup_results.append(f"Historical manager cleanup error: {e}")

        # Cleanup symbol manager  
        try:
            # Symbol manager doesn't have cleanup method, skip
            cleanup_results.append("Symbol manager cleanup not needed")
        except Exception as e:
            logger.warning(f"Error cleaning up symbol manager: {e}")
            cleanup_results.append(f"Symbol manager cleanup error: {e}")

        # Cleanup connection manager (do this last)
        try:
            await self.connection_manager.disconnect()
            cleanup_results.append("Connection manager disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting connection manager: {e}")
            cleanup_results.append(f"Connection manager cleanup error: {e}")

        logger.info(
            f"Rithmic operations cleanup completed: {'; '.join(cleanup_results)}"
        )

    def __str__(self) -> str:
        """String representation of RithmicOperations."""
        return f"RithmicOperations(connected={self.connection_manager.is_connected})"

    def __repr__(self) -> str:
        """Detailed string representation of RithmicOperations."""
        return (
            f"RithmicOperations("
            f"connected={self.connection_manager.is_connected}, "
            f"database_available={hasattr(self, 'database_ops') and self.database_ops is not None})"
        )


# Utility functions for standalone usage
async def create_rithmic_operations(
    progress_callback: Optional[Callable] = None,
) -> RithmicOperationsManager:
    """
    Factory function to create and initialize RithmicOperations.

    Args:
        progress_callback: Optional progress callback

    Returns:
        Initialized RithmicOperationsManager instance
    """
    logger.info("Creating Rithmic operations instance")
    return RithmicOperationsManager(progress_callback)


async def test_rithmic_operations():
    """
    Test function for Rithmic operations.

    This function can be used for basic testing and validation
    of the Rithmic operations coordinator.
    """
    logger.info("Testing Rithmic operations")

    ops = await create_rithmic_operations()

    try:
        # Test connection
        success, message = await ops.test_connection()
        print(f"Connection test: {'SUCCESS' if success else 'FAILED'}")
        print(f"Message: {message}")

        # Get system status
        status = await ops.get_system_status()
        print(f"System status: {status}")

    finally:
        await ops.cleanup()


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run test
    asyncio.run(test_rithmic_operations())
