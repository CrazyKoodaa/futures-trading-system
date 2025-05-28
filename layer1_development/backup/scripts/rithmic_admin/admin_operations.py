"""
Admin Operations and Business Logic for the Enhanced Rithmic Admin Tool
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from async_rithmic import RithmicClient, TimeBarType, InstrumentType, Gateway, DataType
from async_rithmic.client import ReconnectionSettings, RetrySettings
# Fix import path to use absolute path from project root
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import from config
from config.chicago_gateway_config import get_chicago_gateway_config
# Import shared modules
from shared.database.connection import get_async_session, TimescaleDBHelper, get_database_manager

logger = logging.getLogger("rithmic_admin")

class AdminOperations:
    """Core admin operations for the Rithmic tool"""
    
    def __init__(self, status, update_results_callback, display_manager=None):
        self.status = status
        self.update_results = update_results_callback
        self.display_manager = display_manager
        self.rithmic_client: Optional[RithmicClient] = None
    
    async def connect_to_rithmic(self) -> bool:
        """
         with enhanced error handling and diagnostics
         with enhanced error handling and diagnostics
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        connection_start = datetime.now()
        connection_context = {
            'operation': 'rithmic_connect',
            'start_time': connection_start.isoformat()
        }
        
        # Track connection attempts for diagnostics
        if not hasattr(self, '_connection_attempts'):
            self._connection_attempts = 0
        self._connection_attempts += 1
        connection_context['attempt_number'] = self._connection_attempts
        
        logger.info(f"Connecting to Rithmic (attempt {self._connection_attempts})", extra=connection_context)
        
        try:
            # Get configuration with validation
            try:
                config = get_chicago_gateway_config()
                
                # Validate required configuration fields
                required_fields = ['user', 'password', 'system_name', 'app_name', 'app_version', 'gateway']
                missing_fields = [field for field in required_fields if field not in config['rithmic']]
                
                if missing_fields:
                    raise ValueError(f"Missing required Rithmic configuration fields: {', '.join(missing_fields)}")
                
                connection_context['gateway'] = config['rithmic']['gateway']
                connection_context['app_name'] = config['rithmic']['app_name']
                
            except (KeyError, ValueError) as e:
                logger.error(f"Rithmic configuration error: {e}", extra=connection_context)
                self.status.rithmic_connected = False
                self.update_results(f"❌ **Configuration Error**: {e}")
                return False
            
            # Enhanced reconnection settings with better defaults
        Returns:
            bool: True if connection was successful, False otherwis5,  # Increased from e
       """
        connection_start = datetime.now()
        connection_context = {
            'operation': 'rithmic_connect',
            'start_time': connection_start.isoformat()
        }
        
            # Determine gateway with validation
            # Enhanced retry settings3,  # Increased from 
       # Track connection attempts for diagnostics
        if not hasattr(self, '_connection_attempts'Test':
                gateway = Gateway.TEST
            else:
                logger.warning(f"Unknown gateway '{gateway_name}', defaulting to CHICAGO", extra=connection_context)
                gateway = Gateway.CHICAGO
            
            # Initialize Rithmic client with enhanced settingsself._connection_attempts = 0
        self._connection_attempts += 1
        connection_context['attempt_number'] = self._connection_attempts
        
        logger.info(f"Connecting to Rithmic (attempt {self._connection_attempts})", extra=connection_context)
        
        try:
            # Get configuration with validation
            try:
                config = get_chicago_gateway_config()
                
                # Validate required configuration fields
                required_fields = ['user', 'password', 'system_name', 'app_name', 'app_version', 'gateway']
                missing_fields = [field for field in required_fields if field not in config['rithmic']]
                
                if missing_fields:
                    raise ValueError(f"Missing required Rithmic configuration fields: {', '.join(missing_fields)}")
                
                connection_context['gateway'] = config['rithmic']['gateway,
                reconnection_settings=reconnection,
                retry_settings=retry
            )
            
            # Use asyncio.wait_for with progressive timeout
            # If this is a retry, use a longer timeout
            base_timeout = 30.0
            if self._connection_attempts > 1:
                # Increase timeout for subsequent attempts (max 60 seconds)
                timeout = min(base_timeout * (1 + (self._connection_attempts - 1) * 0.5), 60.0)
            else:
                timeout = base_timeout
                
            connection_context['timeout'] = timeout
            
            try:
                # Update UI to show connection attempt
                if hasattr(self, 'update_results'):
                    self.update_results(f"Connecting to Rithmic ({gateway_name})...\nTimeout: {timeout:.1f}s")
                
                # Attempt connection with timeout
                logger.info(f"Attempting Rithmic connection with {timeout:.1f}s timeout", extra=connection_context)
                
                # Use wait_for to handle connection timeouts properly
                await asyncio.wait_for(
                    self.rithmic_client.connect(),
                    timeout=timeout
                )
                
                # Connection successful
                connection_duration = (datetime.now() - connection_start).total_seconds()
                connection_context['duration'] = connection_duration
                
                # Update UI with success message
                if hasattr(self, 'update_results'):
                    self.update_results(
                        f"✅ **Connected to Rithmic**\n\n"
                        f"- **Gateway**: {gateway_name}\n"
                        f"- **User**: {config['rithmic']['user']}\n"
                
                        f"- **Connection time**: {connection_duration:.2f}s"
                  connection_context['status'] = 'timeout'
                connection_context['error'] = 'connection_timeout'
                
                logger.error(
                    f"Rithmic connection timed out after {timeout:.1f}s", 
                    extra=connection_context
                )
                
                
                connection_context['status'] = 'success'
                
                # Update UI with timeout message
                if hasattr(self, 'update_results'):
                    self.update_results(
                        f"❌ **Connection Timeout**\n\n"
                        f"The connection to Rithmic timed out after {timeout:.1f} seconds.\n\n"
                        f"This may be due to:\n"
                        f"- Network connectivity issues\n"
                        f"- High server load\n"
                        f"- Firewall or proxy settings\n\n"
                        f"Please try again or check your network connection."
                    )
                
                
                
                logger.info(
                connection_context['status'] = 'cancelled'
                connection_context['error'] = 'connection_cancelled, extra=connection_context'
                
                    f"Rithmic connection successful in {connection_duration:.2f}s", 
                    extra=connection_contex']
                connection_context['app_name'] = config['rithmic']['app_name']
                
                # Update UI with cancellation message
                if hasattr(self, 'update_results'):
                    self.update_results("❌ **Connection Cancelled**\n\nThe connection attempt was cancelled.")
                
                return False
            
        except Exception as e:
            # Handle any other exceptions
            error_type = type(e).__name__
            error_msg = str(e)
            
            connection_context['status'] = 'error'
            connection_context['error_type'] = error_type
            connection_context['error_message'] = error_msg
            
            logger.exception(
                f"Rithmic connection failed: {error_type} - {error_msg}", 
                extra=connection_context
            )
            
            self.status.rithmic_connected = False
            
            # Update UI with error details
            if hasattr(self, 'update_results'):
                self.update_results(
                    f"❌ **Connection Error**\n\n"
                    f"**Error Type**: {error_type}\n"
                    f"**Message**: {error_msg}\n\n"
                    f"Please check your configuration and network settings."
                )
            
            except (KeyError, ValueError) as e:
                logger.error(f"Rithmic configuration error: {e}", extra=connection_context)
                self.status.rithmic_connected = False
                self.update_results(f"❌ **Configuration Error**: {e}")
                return False
            
            # Enhanced reconnection settings with better defaults
        
        Connect to Rithmic API with enhanced error handling and diagnostics5,  # Increased from 
       
        Returns:
            bool: True if connection was successful, False otherwise
        """
            # Enhanced retry settings
        connection_start = datetime.now()
        connection_context = {
            'operation': 'rithmic_connect3,  # Increased from ',
           'start_time': connection_start.isoformat()
        }
        
            # Determine gateway with validation
        # Track connection attempts for diagnostics
        if not hasattr(self, '_connection_attempts'):
            if gateway_name == 'Chicago':
                self._connection_attempts = 0
        self._connection_attempts += 1
        connection_context['attempt_number'] = self._connection_attemptsTest':
                gateway = Gateway.TEST
            else:
                logger.warning(f"Unknown gateway '{gateway_name}', defaulting to CHICAGO", extra=connection_context)
                gateway = Gateway.CHICAGO
            
            # Initialize Rithmic client with enhanced settings
        logger.info(f"Connecting to Rithmic (attempt {self._connection_attempts})", extra=connection_context)
        
        try:
            # Get configuration with validation
            try:
                config = get_chicago_gateway_config()
                
                # Validate required configuration fields
                required_fields = ['user', 'password', 'system_name', 'app_name', 'app_version', 'gateway,
                reconnection_settings=reconnection,
                retry_settings=retry
            )
            
            # Use asyncio.wait_for with progressive timeout
            # If this is a retry, use a longer timeout
            base_timeout = 30.0
            if self._connection_attempts > 1:
                # Increase timeout for subsequent attempts (max 60 seconds)
                timeout = min(base_timeout * (1 + (self._connection_attempts - 1) * 0.5), 60.0)
            else:
                timeout = base_timeout
                
            connection_context['timeout'] = timeout
            
            try:
                # Update UI to show connection attempt
                if hasattr(self, 'update_results'):
                    self.update_results(f"Connecting to Rithmic ({gateway_name})...\nTimeout: {timeout:.1f}s")
                
                # Attempt connection with timeout
                logger.info(f"Attempting Rithmic connection with {timeout:.1f}s timeout", extra=connection_context)
                
                # Use wait_for to handle connection timeouts properly
                await asyncio.wait_for(
                    self.rithmic_client.connect(),
                    timeout=timeout
                )
                
                # Connection successful
                connection_duration = (datetime.now() - connection_start).total_seconds()
                connection_context['duration'] = connection_duration
                connection_context['status'] = 'success'
                
                
                logger.info(
                    f"Rithmic connection successful in {connection_duration:.2f}s", 
                    extra=connection_contex']
                
                # Update UI with success message
                if hasattr(self, 'update_results'):
                    self.update_results(
                        f"✅ **Connected to Rithmic**\n\n"
                        f"- **Gateway**: {gateway_name}\n"
                        f"- **User**: {config['rithmic']['user']}\n"
                
                        f"- **Connection time**: {connection_duration:.2f}s"
                    )
                
                missing_fields = [field for field in required_fields if field not in config['rithmic']]
                
                
                # Update UI with timeout message
                if hasattr(self, 'update_results'):
                    self.update_results(
                        f"❌ **Connection Timeout**\n\n"
                        f"The connection to Rithmic timed out after {timeout:.1f} seconds.\n\n"
                        f"This may be due to:\n"
                        f"- Network connectivity issues\n"
                        f"- High server load\n"
                        f"- Firewall or proxy settings\n\n"
                        f"Please try again or check your network connection."
                    )
                
                if missing_fields:
                    raise ValueError(f"Missing required Rithmic configuration fields: {', '.join(missing_fields)}")
                
                connection_context['gateway'] = config['rithmic']['gateway']
                connection_context['app_name'] = config['rithmic']['app_name']
                
                
            except (KeyError, ValueError) as e:
                connection_context['status'] = 'cancelled'
                connection_context['error'] = 'connection_cancelled, extra=connection_context'
                
                logger.error(f"Rithmic configuration error: {e}", extra=connection_context)
                self.status.rithmic_connected = False
                self.update_results(f"❌ **Configuration Error**: {e}")
                return False
            
                # Update UI with cancellation message
                if hasattr(self, 'update_results'):
                    self.update_results("❌ **Connection Cancelled**\n\nThe connection attempt was cancelled.")
                
                return False
            
        except Exception as e:
            # Handle any other exceptions
            error_type = type(e).__name__
            error_msg = str(e)
            
            connection_context['status'] = 'error'
            connection_context['error_type'] = error_type
            connection_context['error_message'] = error_msg
            
            logger.exception(
                f"Rithmic connection failed: {error_type} - {error_msg}", 
                extra=connection_context
            )
            
            self.status.rithmic_connected = False
            
            # Update UI with error details
            if hasattr(self, 'update_results'):
                self.update_results(
                    f"❌ **Connection Error**\n\n"
                    f"**Error Type**: {error_type}\n"
                    f"**Message**: {error_msg}\n\n"
                    f"Please check your configuration and network settings."
                )
            
            # Enhanced reconnection settings with better defaults
            reconnection = ReconnectionSettings(
                max_retries=5,  # Increased from 3
                backoff_type="exponential",
                interval=2,
                max_delay=45,  # Increased from 30
                jitter_range=(0.5, 1.5)
            )
            
            # Enhanced retry settings
            retry = RetrySettings(
                max_retries=3,  # Increased from 2
                timeout=30.0,  # Increased from 20
                jitter_range=(0.5, 1.5)
            )
            
            # Determine gateway with validation
            gateway_name = config['rithmic']['gateway']
            if gateway_name == 'Chicago':
                gateway = Gateway.CHICAGO
            elif gateway_name == 'Test':
                gateway = Gateway.TEST
            else:
                logger.warning(f"Unknown gateway '{gateway_name}', defaulting to CHICAGO", extra=connection_context)
                gateway = Gateway.CHICAGO
            
            # Initialize Rithmic client with enhanced settings
            self.rithmic_client = RithmicClient(
                user=config['rithmic']['user'],
                password=config['rithmic']['password'],
                system_name=config['rithmic']['system_name'],
                app_name=config['rithmic']['app_name'],
                app_version=config['rithmic']['app_version'],
                gateway=gateway,
                reconnection_settings=reconnection,
                retry_settings=retry
            )
            
            # Use asyncio.wait_for with progressive timeout
            # If this is a retry, use a longer timeout
            base_timeout = 30.0
            if self._connection_attempts > 1:
                # Increase timeout for subsequent attempts (max 60 seconds)
                timeout = min(base_timeout * (1 + (self._connection_attempts - 1) * 0.5), 60.0)
            else:
                timeout = base_timeout
                
            connection_context['timeout'] = timeout
            
            try:
                # Update UI to show connection attempt
                if hasattr(self, 'update_results'):
                    self.update_results(f"Connecting to Rithmic ({gateway_name})...\nTimeout: {timeout:.1f}s")
                
                # Attempt connection with timeout
                logger.info(f"Attempting Rithmic connection with {timeout:.1f}s timeout", extra=connection_context)
                
                # Use wait_for to handle connection timeouts properly
                await asyncio.wait_for(
                    self.rithmic_client.connect(),
                    timeout=timeout
                )
                
                # Connection successful
                connection_duration = (datetime.now() - connection_start).total_seconds()
                connection_context['duration'] = connection_duration
                connection_context['status'] = 'success'
                
                logger.info(
                    f"Rithmic connection successful in {connection_duration:.2f}s", 
                    extra=connection_context
                )
                
                self.status.rithmic_connected = True
                
                # Update UI with success message
                if hasattr(self, 'update_results'):
                    self.update_results(
                        f"✅ **Connected to Rithmic**\n\n"
                        f"- **Gateway**: {gateway_name}\n"
                        f"- **User**: {config['rithmic']['user']}\n"
                        f"- **Connection time**: {connection_duration:.2f}s"
                    )
                
                return True
                
            except asyncio.TimeoutError:
                connection_context['status'] = 'timeout'
                connection_context['error'] = 'connection_timeout'
                
                logger.error(
                    f"Rithmic connection timed out after {timeout:.1f}s", 
                    extra=connection_context
                )
                
                self.status.rithmic_connected = False
                
                # Update UI with timeout message
                if hasattr(self, 'update_results'):
                    self.update_results(
                        f"❌ **Connection Timeout**\n\n"
                        f"The connection to Rithmic timed out after {timeout:.1f} seconds.\n\n"
                        f"This may be due to:\n"
                        f"- Network connectivity issues\n"
                        f"- High server load\n"
                        f"- Firewall or proxy settings\n\n"
                        f"Please try again or check your network connection."
                    )
                
                return False
                
            except asyncio.CancelledError:
                connection_context['status'] = 'cancelled'
                connection_context['error'] = 'connection_cancelled'
                
                logger.error("Rithmic connection was cancelled", extra=connection_context)
                self.status.rithmic_connected = False
                
                # Update UI with cancellation message
                if hasattr(self, 'update_results'):
                    self.update_results("❌ **Connection Cancelled**\n\nThe connection attempt was cancelled.")
                
                return False
            
        except Exception as e:
            # Handle any other exceptions
            error_type = type(e).__name__
            error_msg = str(e)
            
            connection_context['status'] = 'error'
            connection_context['error_type'] = error_type
            connection_context['error_message'] = error_msg
            
            logger.exception(
                f"Rithmic connection failed: {error_type} - {error_msg}", 
                extra=connection_context
            )
            
            self.status.rithmic_connected = False
            
            # Update UI with error details
            if hasattr(self, 'update_results'):
                self.update_results(
                    f"❌ **Connection Error**\n\n"
                    f"**Error Type**: {error_type}\n"
                    f"**Message**: {error_msg}\n\n"
                    f"Please check your configuration and network settings."
                )
            
            return False
    
    async def disconnect_from_rithmic(self, timeout=5.0):
        """
        Disconnect from Rithmic API with enhanced cleanup and error handling
        
        Args:
            timeout: Maximum time to wait for disconnection (seconds)
            
        Returns:
            bool: True if disconnection was successful or client was already disconnected
        """
        disconnect_start = datetime.now()
        disconnect_context = {
            'operation': 'rithmic_disconnect',
            'start_time': disconnect_start.isoformat(),
            'timeout': timeout
        }
        
        logger.info(f"Disconnecting from Rithmic (timeout: {timeout}s)")
        
        # If client doesn't exist, nothing to disconnect
        if not self.rithmic_client:
            logger.info("No active Rithmic client to disconnect")
            self.status.rithmic_connected = False
            return True
            
        try:
            # Use asyncio.wait_for to handle disconnection timeouts
            try:
                # First, attempt a clean disconnect
                logger.debug("Attempting clean disconnect from Rithmic")
                
                # Capture stderr to suppress disconnect warnings
                import sys
                from io import StringIO
                original_stderr = sys.stderr
                string_buffer = StringIO()
                
                try:
                    sys.stderr = string_buffer
                    await asyncio.wait_for(
                        self.rithmic_client.disconnect(),
                        timeout=timeout
                    )
                    
                    disconnect_duration = (datetime.now() - disconnect_start).total_seconds()
                    logger.info(f"Rithmic disconnected successfully in {disconnect_duration:.2f}s")
                    
                except asyncio.TimeoutError:
                    # If clean disconnect times out, force cleanup
                    logger.warning(f"Rithmic disconnection timed out after {timeout}s, forcing cleanup")
                    
                    # Force cleanup of any resources
                    try:
                        # Close any open connections or resources
                        if hasattr(self.rithmic_client, '_session') and self.rithmic_client._session:
                            if not self.rithmic_client._session.closed:
                                await self.rithmic_client._session.close()
                                
                        logger.info("Forced cleanup of Rithmic client resources completed")
                        
                    except Exception as cleanup_error:
                        logger.error(f"Error during forced cleanup: {cleanup_error}")
                    
                except asyncio.CancelledError:
                    logger.warning("Rithmic disconnection was cancelled")
                    
                except Exception as disconnect_error:
                    logger.error(f"Error during disconnect: {disconnect_error}")
                
                finally:
                    sys.stderr = original_stderr
                
            finally:
                # Always set client to None to ensure it's not reused
                # and update connection status
                self.rithmic_client = None
                self.status.rithmic_connected = False
                
                # Perform garbage collection to clean up any lingering resources
                try:
                    import gc
                    gc.collect()
                    logger.debug("Garbage collection performed after disconnect")
                except ImportError:
                    pass
                
            return True
            
        except Exception as e:
            # Handle any unexpected exceptions during the entire process
            error_type = type(e).__name__
            error_msg = str(e)
            
            logger.exception(f"Unexpected error disconnecting from Rithmic: {error_type} - {error_msg}")
            
            # Always ensure we update the connection status
            self.status.rithmic_connected = False
            
            # Set client to None even on error to prevent reuse
            self.rithmic_client = None
            
            return False
                # Continue with cleanup even after timeout
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                # Always mark as disconnected and clean up client reference
                self.status.rithmic_connected = False
                self.rithmic_client = None
    
    async def test_connections(self):
        """Test database and Rithmic connections"""
        results = "## 🔍 Connection Test Results\n\n"
        
        # Test database
        try:
            db_manager = get_database_manager()
            connection_ok = await db_manager.test_connection()
            if connection_ok:
                results += "✅ **TimescaleDB**: Connection successful\n"
                self.status.db_connected = True
                
                # Verify tables exist
                async with get_async_session() as session:
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds LIMIT 1"))
                    results += "✅ **Tables**: Accessible\n"
            else:
                results += "❌ **TimescaleDB**: Connection failed\n"
                self.status.db_connected = False
        except Exception as e:
            results += f"❌ **TimescaleDB**: Error - {str(e)}\n"
            self.status.db_connected = False
        
        # Test Rithmic
        try:
            await self.connect_to_rithmic()
            if self.status.rithmic_connected:
                results += "✅ **Rithmic**: Connection successful\n"
            else:
                results += "❌ **Rithmic**: Connection failed\n"
        except Exception as e:
            results += f"❌ **Rithmic**: Error - {str(e)}\n"
        
        results += f"\n**Summary**: {'✅ Ready' if self.status.rithmic_connected and self.status.db_connected else '⚠️ Issues detected'}"
        self.update_results(results)
    
    async def search_symbols_and_contracts(self):
        """Search for symbols and check contracts with interactive selection"""
        if not self.status.rithmic_connected:
            self.update_results("❌ **Error**: Not connected to Rithmic. Please test connections first.")
            return
        
        # First, prompt for symbol search pattern
        self.update_results("## 🔍 Symbol Search\n\nEnter symbol pattern to search (e.g., ES*, NQ?, *)\nUse * for wildcard, ? for single character")
        
        try:
            # Get symbol pattern from user with popup dialog
            symbol_pattern = await self._get_user_input(
                "Enter symbol pattern to search (e.g., ES*, NQ?, *)\nUse * for wildcard, ? for single character", 
                title="Symbol Search"
            )
            if not symbol_pattern:
                symbol_pattern = "*"  # Default to all symbols
                self.status.add_log_message("Using default symbol pattern: *")
        except Exception as e:
            symbol_pattern = "*"  # Default to all symbols
            self.status.add_log_message(f"Error getting symbol pattern: {str(e)}")
            logger.error(f"Error in symbol pattern input: {str(e)}")
            
        self.status.add_log_message(f"Searching with pattern: {symbol_pattern}")
        logger.info(f"Searching with pattern: {symbol_pattern} in exchange: {self.status.current_exchange}")
        
        # Search for symbols matching the pattern
        try:
            # Convert pattern to regex-like format for Rithmic API
            search_pattern = symbol_pattern.replace('*', '%').replace('?', '_')
            
            # Show searching message
            self.update_results(f"## 🔍 Searching for: {symbol_pattern}\n\nPlease wait...")
            
            # Search for symbols
            search_results = await self._search_symbols(search_pattern, InstrumentType.FUTURE, self.status.current_exchange)
            
            if not search_results:
                self.update_results(f"## 🔍 Symbol Search Results\n\n❌ No symbols found matching '{symbol_pattern}'")
                self.status.add_log_message(f"No symbols found for pattern: {symbol_pattern}")
                return
                
            # Log the search results
            logger.info(f"Found {len(search_results)} results for pattern: {symbol_pattern}")
            self.status.add_log_message(f"Found {len(search_results)} matching contracts")
            
            # Group results by product code
            grouped_results = {}
            for contract in search_results:
                product_code = contract.get('product_code', 'UNKNOWN')
                if product_code not in grouped_results:
                    grouped_results[product_code] = []
                grouped_results[product_code].append(contract)
            
            # Display grouped results for selection
            results = "## 🔍 Symbol Search Results\n\n"
            results += f"Found {len(search_results)} contracts in {len(grouped_results)} product groups\n\n"
            
            # Create a list of product codes for selection
            product_codes = sorted(grouped_results.keys())
            
            for i, product_code in enumerate(product_codes):
                contracts = grouped_results[product_code]
                results += f"{i+1}. **{product_code}** ({len(contracts)} contracts)\n"
            
            results += "\nSelect a product group by number to view available contracts"
            self.update_results(results)
            
            try:
                # Get user selection using popup dialog with options
                options = [f"{code} ({len(grouped_results[code])} contracts)" for code in product_codes]
                selection = await self._get_user_input(
                    "Select a product group to view available contracts:", 
                    title="Product Group Selection",
                    options=options
                )
                
                if selection:
                    try:
                        # Extract the product code from the selection (format: "CODE (X contracts)")
                        selected_product = selection.split(" ")[0]
                        if selected_product in product_codes:
                            await self._display_contracts_for_selection(selected_product, grouped_results[selected_product])
                        else:
                            # Fallback to first product if extraction fails
                            selected_product = product_codes[0]
                            self.status.add_log_message(f"Invalid product selection, using {selected_product}")
                            await self._display_contracts_for_selection(selected_product, grouped_results[selected_product])
                    except Exception as e:
                        self.update_results(f"❌ Error processing selection: {str(e)}")
                        logger.error(f"Error processing product selection: {str(e)}")
                else:
                    self.update_results("❌ Selection cancelled. Please try again.")
            except Exception as e:
                self.update_results(f"❌ Error during product selection: {str(e)}")
                logger.error(f"Error during product selection: {str(e)}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = f"Error during symbol search: {str(e)}"
            self.update_results(f"## ❌ Search Error\n\n{error_msg}")
            logger.error(error_msg)
            logger.debug(f"Detailed error: {error_details}")
            self.status.add_log_message(f"Error: {error_msg}")
    
    async def _get_user_input(self, prompt, title="User Input", options=None):
        """Get user input with a popup dialog"""
        self.status.add_log_message(f"Waiting for input: {prompt}")
        
        # Use popup dialog if display manager is available
        if self.display_manager:
            user_input = self.display_manager.show_popup_dialog(title, prompt, options)
        else:
            # Fallback to console input
            self.update_results(f"{prompt}")
            user_input = input(prompt).strip()
        
        if user_input:
            self.status.add_log_message(f"User entered: {user_input}")
        else:
            self.status.add_log_message("User cancelled input")
            
        return user_input
        
    async def _display_contracts_for_selection(self, product_code, contracts):
        """Display contracts for a product code and allow selection"""
        # Sort contracts by expiration date
        sorted_contracts = sorted(contracts, key=lambda x: x.get('expiration_date', '') or x.get('symbol', ''))
        
        results = f"## 📊 Contracts for {product_code}\n\n"
        
        for i, contract in enumerate(sorted_contracts):
            symbol = contract.get('symbol', 'Unknown')
            expiry = contract.get('expiration_date', 'Unknown')
            description = contract.get('description', '')
        Download historical data with optimized performance and error handling.
        
        Args:
            helper: Database helper for inserting data
            contract: Contract identifier
            symbol: Symbol name
            start_time: Start time for data download
            end_time: End time for data download
            data_type: Type of data to download ("second" or "minute")
            
        Returns:
            None
        
        Raises:
            ConnectionError: If Rithmic client is not initialized
        """
        if data_type == "second":
            bar_type = TimeBarType.SECOND_BAR
            table_name = 'market_data_seconds'
        else:
            bar_type = TimeBarType.MINUTE_BAR
            table_name = 'market_data_minutes'
        
        # Optimize chunk size based on data type
        # Smaller chunks for seconds data to avoid memory issues
        # Larger chunks for minute data for better throughput
        chunk_size = timedelta(hours=4) if data_type == "second" else timedelta(days=3)
        
        # Calculate number of chunks for progress tracking
        total_duration = (end_time - start_time).total_seconds()
        chunk_duration = chunk_size.total_seconds()
        total_chunks = max(1, int(total_duration / chunk_duration) + 1)
        
        # Track performance metrics
        download_start_time = datetime.now()
        total_bars = 0
        failed_chunks = 0
        
        # Create time chunks for download
        time_chunks = []
        current_start = start_time
        while current_start < end_time:
            current_end = min(end_time, current_start + chunk_size)
            time_chunks.append((current_start, current_end))
            current_start = current_end
        
        # Process chunks with semaphore to limit concurrency
        # This prevents overwhelming the Rithmic API
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests
        all_bars = []
        
        async def process_chunk(chunk_idx, chunk_start, chunk_end):
            """Process a single time chunk with proper error handling"""
            nonlocal failed_chunks
            
            async with semaphore:
                chunk_id = f"{contract}_{data_type}_{chunk_idx}"
                logger.debug(f"Downloading chunk {chunk_idx+1}/{len(time_chunks)}: {chunk_start} to {chunk_end}")
                
                # Update progress in UI
                if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                    self.status.download_progress[chunk_id] = {
                        'progress': chunk_idx / len(time_chunks),
                        'status': 'downloading'
                    }
                
                try:
                    if not self.rithmic_client:
                        logger.error("Rithmic client is not initialized")
                        raise ConnectionError("Rithmic client is not initialized")
                    
                    # Add timeout to prevent hanging requests
                    chunk_bars = await asyncio.wait_for(
                        self.rithmic_client.get_historical_time_bars(
                            contract,
                            self.status.current_exchange,
                            chunk_start,
                            chunk_end,
                            bar_type,
                            1
                        ),
                        timeout=60.0  # 60 second timeout per chunk
                    )
                    
                    # Update progress in UI
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 1.0,
                            'status': 'complete'
                        }
                    
                    return chunk_bars
                    
                except asyncio.TimeoutError:
                    failed_chunks += 1
                    logger.error(f"Timeout downloading chunk {chunk_idx+1}/{len(time_chunks)} for {contract}")
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 0,
                            'status': 'timeout'
                        }
                    return []
                    
                except Exception as e:
                    failed_chunks += 1
                    logger.error(f"Error downloading chunk {chunk_idx+1}/{len(time_chunks)} for {contract}: {e}")
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
            
                        self.status.download_progress[chunk_id] = {
                            'progress': 0,
                            'status': 'error'
                        }
                    return []
        
        # Create tasks for all chunks
        tasks = [process_chunk(i, chunk[0], chunk[1]) for i, chunk in enumerate(time_chunks)]
        
        # Wait for all tasks to complete and gather results
        chunk_results = await asyncio.gather(*tasks)
        
        # Combine all results
        for chunk_bars in chunk_results:
            if chunk_bars:
                all_bars.extend(chunk_bars)
                total_bars += len(chunk_bars)
        
        # Calculate performance metrics
        download_duration = (datetime.now() - download_start_time).total_seconds()
        bars_per_second = total_bars / max(1, download_duration)
        
        logger.info(f"Downloaded {total_bars} {data_type} bars in {download_duration:.2f}s ({bars_per_second:.2f} bars/s)")
        logger.info(f"Failed chunks: {failed_chunks}/{len(time_chunks)}")
       try:
                    record = {
                        'timestamp': bar.get('bar_end_datetime', datetime.now()),
                        'symbol': symbol,
                        'contract': contract,
                        'exchange': self.status.current_exchange,
                        'exchange_code': 'XCME' if self.status.current_exchange == 'CME' else self.status.current_exchange,
                        'open': float(bar.get('open', 0)),
                        'high': float(bar.get('high', 0)),
                        'low': float(bar.get('low', 0)),
                        'close': float(bar.get('close', 0)),
                        'volume': int(bar.get('volume', 0)),
                        'tick_count': int(bar.get('tick_count', 1)),
                        'vwap': float(bar.get('vwap', bar.get('close', 0))),
                        'bid': None,
                        'ask': None,
                        'spread': None,
                        'data_quality_score': 1.0,
                        'is_regular_hours': True
                    }
                    data_records.append(record)
                    
                    # Insert in batches to avoid memory issues with large datasets
                    if len(data_records) >= batch_size:
                        await helper.bulk_insert_market_data(data_records, table_name)
                        data_records = []
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing bar data: {e}, bar: {bar}")
            
            # Insert any remaining records
            if data_records:
                await helper.bulk_insert_market_data(data_records, table_name)
                
            logger.info(f"Inserted {total_bars} {data_type} bars into {table_name}" 
        # Save to database with batching for better performance
        if all_bars:
            # Process in batches of 5000 records for better database performance
            batch_size = 5000
            
            results += f"{i+1}. **{symbol}** - Expires: {expiry}\n"
            if description:
                results += f"   {description}\n"
        
        results += "\nSelect contracts by number to use for data download"
        self.update_results(results)
        
        # Create options list for the popup dialog
        options = []
        for contract in sorted_contracts:
            symbol = contract.get('symbol', 'Unknown')
            expiry = contract.get('expiration_date', 'Unknown')
            description = contract.get('description', '')
            option_text = f"{symbol} - Expires: {expiry}"
            if description:
                option_text += f" - {description}"
            options.append(option_text)
        
        # Get user selection using popup dialog
        selection = await self._get_user_input(
            f"Select a contract for {product_code}:",
            title="Contract Selection",
            options=options
        )
        
        if selection:
            # Extract the symbol from the selection (format: "SYMBOL - Expires: DATE")
            selected_symbol = selection.split(" - ")[0]
            
            # Find the selected contract
            selected_contract = next((c for c in sorted_contracts if c.get('symbol') == selected_symbol), None)
            
            if selected_contract:
                # Store the selected contract
                self.status.current_symbols = [product_code]
                self.status.available_contracts[product_code] = [selected_symbol]
                
                # Show confirmation
                confirmation = f"## ✅ Contract Selected\n\n"
                confirmation += f"Product: **{product_code}**\n"
                confirmation += f"Contract: **{selected_symbol}**\n"
                confirmation += f"Expiration: {selected_contract.get('expiration_date', 'Unknown')}\n\n"
                
                # Check database data if connected
                if self.status.db_connected:
                    try:
                        async with get_async_session() as session:
                            from sqlalchemy import text
                            result = await session.execute(
                                text("SELECT COUNT(*) FROM market_data_seconds WHERE symbol = :symbol"),
                                {'symbol': product_code}
                            )
                            count = result.scalar()
                            confirmation += f"💾 Database records: {count:,}\n"
                            self.status.add_log_message(f"DB records for {product_code}: {count:,}")
                    except Exception as e:
                        error_msg = f"Database check failed: {str(e)}"
                        confirmation += f"⚠️ {error_msg}\n"
                        logger.error(error_msg)
                
                confirmation += "\nReady for data download with this contract."
                self.update_results(confirmation)
                
                # Log the selection
                self.status.add_log_message(f"Selected contract: {selected_symbol} for {product_code}")
                logger.info(f"User selected contract: {selected_symbol} for product: {product_code}")
            else:
                self.update_results("❌ Error finding selected contract. Please try again.")
        else:
            self.update_results("❌ Selection cancelled. Please try again.")
    
    async def _search_symbols(self, search_term: str, instrument_type, exchange: str):
        """Search for symbols using Rithmic API"""
        if not self.rithmic_client:
            logger.error("Rithmic client is not initialized")
            return []
        
        try:
            logger.info(f"Searching for symbol: {search_term} in exchange: {exchange}")
            results = await self.rithmic_client.search_symbols(
                search_term,
                instrument_type=instrument_type,
                exchange=exchange
            )
            return results
        except Exception as e:
            # Get detailed error information
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error searching for symbol {search_term}: {str(e)}")
            logger.debug(f"Detailed error for symbol search {search_term}: {error_details}")
            return []
    
    async def _get_front_month_contract(self, symbol: str, exchange: str):
        """Get front month contract for a symbol"""
        try:
            # Get search results
            results = await self._search_symbols(symbol, InstrumentType.FUTURE, exchange)
            
            # Log the raw results for debugging
            logger.info(f"Search results for {symbol}: Found {len(results)} contracts")
            
            # Filter contracts
            filtered_contracts = [r for r in results if r.get('product_code') and r['product_code'].startswith(symbol)]
            logger.info(f"Filtered contracts for {symbol}: Found {len(filtered_contracts)} matching contracts")
            
            if filtered_contracts:
                # Sort contracts by expiration date or symbol if expiration date is not available
                sorted_contracts = sorted(filtered_contracts, key=lambda x: x.get('expiration_date', '') or x.get('symbol', ''))
                front_month = sorted_contracts[0].get('symbol') if sorted_contracts else None
                logger.info(f"Selected front month for {symbol}: {front_month}")
                return front_month
            else:
                logger.warning(f"No matching contracts found for {symbol} in {exchange}")
                return None
        except Exception as e:
            # Get detailed error information
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error getting front month contract for {symbol}: {str(e)}")
            logger.debug(f"Detailed error for {symbol}: {error_details}")
            return None
    
    async def view_database_data(self):
        """View TimescaleDB data with detailed information"""
        if not self.status.db_connected:
            self.update_results("❌ **Error**: Not connected to TimescaleDB. Please test connections first.")
            return
        
        results = "## 📊 Database Information\n\n"
        
        try:
            async with get_async_session() as session:
                from sqlalchemy import text
                
                # Table counts
                tables = ['market_data_seconds', 'market_data_minutes', 'predictions', 'trades']
                results += "### Table Summary\n"
                
                for table in tables:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        Download historical data with optimized performance and error handling.
        
        Args:
            helper: Database helper for inserting data
            contract: Contract identifier
            symbol: Symbol name
            start_time: Start time for data download
            end_time: End time for data download
            data_type: Type of data to download ("second" or "minute")
            
        Returns:
            None
        
        Raises:
            ConnectionError: If Rithmic client is not initialized
        """
        if data_type == "second":
            bar_type = TimeBarType.SECOND_BAR
            table_name = 'market_data_seconds'
        else:
            bar_type = TimeBarType.MINUTE_BAR
            table_name = 'market_data_minutes'
        
        # Optimize chunk size based on data type
        # Smaller chunks for seconds data to avoid memory issues
        # Larger chunks for minute data for better throughput
        chunk_size = timedelta(hours=4) if data_type == "second" else timedelta(days=3)
        
        # Calculate number of chunks for progress tracking
        total_duration = (end_time - start_time).total_seconds()
        chunk_duration = chunk_size.total_seconds()
        total_chunks = max(1, int(total_duration / chunk_duration) + 1)
        
        # Track performance metrics
        download_start_time = datetime.now()
        total_bars = 0
        failed_chunks = 0
        
        # Create time chunks for download
        time_chunks = []
        current_start = start_time
        while current_start < end_time:
            current_end = min(end_time, current_start + chunk_size)
            time_chunks.append((current_start, current_end))
            current_start = current_end
        
        # Process chunks with semaphore to limit concurrency
        # This prevents overwhelming the Rithmic API
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests
        all_bars = []
        
        async def process_chunk(chunk_idx, chunk_start, chunk_end):
            """Process a single time chunk with proper error handling"""
            nonlocal failed_chunks
            
            async with semaphore:
                chunk_id = f"{contract}_{data_type}_{chunk_idx}"
                logger.debug(f"Downloading chunk {chunk_idx+1}/{len(time_chunks)}: {chunk_start} to {chunk_end}")
                
                # Update progress in UI
                if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                    self.status.download_progress[chunk_id] = {
                        'progress': chunk_idx / len(time_chunks),
                        'status': 'downloading'
                    }
                
                try:
                    if not self.rithmic_client:
                        logger.error("Rithmic client is not initialized")
                        raise ConnectionError("Rithmic client is not initialized")
                    
                    # Add timeout to prevent hanging requests
                    chunk_bars = await asyncio.wait_for(
                        self.rithmic_client.get_historical_time_bars(
                            contract,
                            self.status.current_exchange,
                            chunk_start,
                            chunk_end,
                            bar_type,
                            1
                        ),
                        timeout=60.0  # 60 second timeout per chunk
                    )
                    
                    # Update progress in UI
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 1.0,
                            'status': 'complete'
                        }
                    
                    return chunk_bars
                    
                except asyncio.TimeoutError:
                    failed_chunks += 1
                    logger.error(f"Timeout downloading chunk {chunk_idx+1}/{len(time_chunks)} for {contract}")
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 0,
                            'status': 'timeout'
                        }
                    return []
                    
                except Exception as e:
                    failed_chunks += 1
            
                    logger.error(f"Error downloading chunk {chunk_idx+1}/{len(time_chunks)} for {contract}: {e}")
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 0,
                            'status': 'error'
                        }
                    return []
        
        # Create tasks for all chunks
        tasks = [process_chunk(i, chunk[0], chunk[1]) for i, chunk in enumerate(time_chunks)]
        
        # Wait for all tasks to complete and gather results
        chunk_results = await asyncio.gather(*tasks)
        
        # Combine all results
        for chunk_bars in chunk_results:
            if chunk_bars:
                all_bars.extend(chunk_bars)
                total_bars += len(chunk_bars)
        
        # Calculate performance metrics
        download_duration = (datetime.now() - download_start_time).total_seconds()
        bars_per_second = total_bars / max(1, download_duration)
        try:
                    record = {
                        'timestamp': bar.get('bar_end_datetime', datetime.now()),
                        'symbol': symbol,
                        'contract': contract,
                        'exchange': self.status.current_exchange,
                        'exchange_code': 'XCME' if self.status.current_exchange == 'CME' else self.status.current_exchange,
                        'open': float(bar.get('open', 0)),
                        'high': float(bar.get('high', 0)),
                        'low': float(bar.get('low', 0)),
                        'close': float(bar.get('close', 0)),
                        'volume': int(bar.get('volume', 0)),
                        'tick_count': int(bar.get('tick_count', 1)),
                        'vwap': float(bar.get('vwap', bar.get('close', 0))),
                        'bid': None,
                        'ask': None,
                        'spread': None,
                        'data_quality_score': 1.0,
                        'is_regular_hours': True
                    }
                    data_records.append(record)
                    
                    # Insert in batches to avoid memory issues with large datasets
                    if len(data_records) >= batch_size:
                        await helper.bulk_insert_market_data(data_records, table_name)
                        data_records = []
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing bar data: {e}, bar: {bar}")
            
            # Insert any remaining records
            if data_records:
                await helper.bulk_insert_market_data(data_records, table_name)
                
            logger.info(f"Inserted {total_bars} {data_type} bars into {table_name}"
        logger.info(f"Downloaded {total_bars} {data_type} bars in {download_duration:.2f}s ({bars_per_second:.2f} bars/s)")
        logger.info(f"Failed chunks: {failed_chunks}/{len(time_chunks)}")
        
        # Save to database with batching for better performance
        if all_bars:
            # Process in batches of 5000 records for better database performance
            batch_size = 5000
                        count = result.scalar()
                        results += f"- **{table}**: {count:,} records\n"
                    except Exception as e:
                        results += f"- **{table}**: Error - {str(e)}\n"
                
                # Symbol breakdown
                result = await session.execute(text("""
                    SELECT symbol, exchange, COUNT(*) as count,
                           MIN(timestamp) as first_data,
                           MAX(timestamp) as last_data
                    FROM market_data_seconds
                    GROUP BY symbol, exchange
                    ORDER BY count DESC
                    LIMIT 10
                """))
                symbols_data = result.fetchall()
                
                if symbols_data:
                    results += "\n### Top Symbols by Data Volume\n"
                    for row in symbols_data:
                        results += f"- **{row[0]}** ({row[1]}): {row[2]:,} records\n"
                        results += f"  - First: {str(row[3])[:19] if row[3] else 'N/A'}\n"
                        results += f"  - Last: {str(row[4])[:19] if row[4] else 'N/A'}\n"
                
                # Recent data sample
                result = await session.execute(text("""
                    SELECT symbol, contract, timestamp, close, volume
                    FROM market_data_seconds
                    ORDER BY timestamp DESC
                    LIMIT 5
                """))
                recent_data = result.fetchall()
                
                if recent_data:
                    results += "\n### Recent Data Sample\n"
                    for row in recent_data:
                        results += f"- **{row[0]}** {row[1]} @ {str(row[2])[:19]}: ${row[3]:.2f} (Vol: {row[4]})\n"
                
        except Exception as e:
            results += f"❌ **Error**: {str(e)}\n"
        
        self.update_results(results)
    
    async def download_historical_data(self, days: int = 7):
        """Download historical data with progress tracking"""
        if not self.status.rithmic_connected or not self.status.db_connected:
            self.update_results("❌ **Error**: Both Rithmic and Database connections required")
            return
            
        if not self.status.available_contracts:
            self.update_results("❌ **Error**: No contracts available. Search symbols first.")
            return
        
        # Initialize progress tracking
        self.status.download_progress = {}
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        results = f"## 📥 Historical Data Download\n\n**Period**: {days} days ({start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')})\n\n"
        
        try:
            async with get_async_session() as session:
                helper = TimescaleDBHelper(session)
                
                for symbol, contracts in self.status.available_contracts.items():
                    for contract in contracts:
                        results += f"### Processing {contract}\n"
                        
                        # Download second bars
                        try:
                            await self._download_data_simple(helper, contract, symbol, start_time, end_time, "second")
                            results += f"✅ **Second bars**: Downloaded successfully\n"
                        except Exception as e:
                            results += f"❌ **Second bars**: Error - {str(e)}\n"
                        
                        # Download minute bars
                        try:
                            await self._download_data_simple(helper, contract, symbol, start_time, end_time, "minute")
                            results += f"✅ **Minute bars**: Downloaded successfully\n"
                        except Exception as e:
                            results += f"❌ **Minute bars**: Error - {str(e)}\n"
                        
                        results += "\n"
        
        except Exception as e:
            results += f"❌ **Fatal Error**: {str(e)}\n"
        
        # Verify data insertion
        try:
            async with get_async_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
                second_count = result.scalar()
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
                minute_count = result.scalar()
                
                results += f"### Final Database Status\n"
                results += f"- **Second bars**: {second_count:,} total records\n"
                results += f"- **Minute bars**: {minute_count:,} total records\n"
        except Exception as e:
            results += f"⚠️ **Verification Error**: {str(e)}\n"
        
        self.update_results(results)
    
    async def _download_data_simple(self, helper: TimescaleDBHelper, contract: str, symbol: str,
                                  start_time: datetime, end_time: datetime, data_type: str):
        """
        Download historical data with optimized performance and error handling.
        
        Args:
            helper: Database helper for inserting data
            contract: Contract identifier
            symbol: Symbol name
            start_time: Start time for data download
            end_time: End time for data download
            data_type: Type of data to download ("second" or "minute")
            
        Returns:
            None
        
        Raises:
            ConnectionError: If Rithmic client is not initialized
        """
        if data_type == "second":
            bar_type = TimeBarType.SECOND_BAR
            table_name = 'market_data_seconds'
        else:
            bar_type = TimeBarType.MINUTE_BAR
            table_name = 'market_data_minutes'
        
        # Optimize chunk size based on data type
        # Smaller chunks for seconds data to avoid memory issues
        # Larger chunks for minute data for better throughput
        chunk_size = timedelta(hours=4) if data_type == "second" else timedelta(days=3)
        
        # Calculate number of chunks for progress tracking
        total_duration = (end_time - start_time).total_seconds()
        chunk_duration = chunk_size.total_seconds()
        total_chunks = max(1, int(total_duration / chunk_duration) + 1)
        
        # Track performance metrics
        download_start_time = datetime.now()
        total_bars = 0
        failed_chunks = 0
        
        # Create time chunks for download
        time_chunks = []
        current_start = start_time
        while current_start < end_time:
            current_end = min(end_time, current_start + chunk_size)
            time_chunks.append((current_start, current_end))
            current_start = current_end
        
        # Process chunks with semaphore to limit concurrency
        # This prevents overwhelming the Rithmic API
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests
        all_bars = []
        
        async def process_chunk(chunk_idx, chunk_start, chunk_end):
            """Process a single time chunk with proper error handling"""
            nonlocal failed_chunks
            
            async with semaphore:
                chunk_id = f"{contract}_{data_type}_{chunk_idx}"
                logger.debug(f"Downloading chunk {chunk_idx+1}/{len(time_chunks)}: {chunk_start} to {chunk_end}")
                
                # Update progress in UI
                if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                    self.status.download_progress[chunk_id] = {
                        'progress': chunk_idx / len(time_chunks),
                        'status': 'downloading'
                    }
                
                try:
                    if not self.rithmic_client:
                        logger.error("Rithmic client is not initialized")
                        raise ConnectionError("Rithmic client is not initialized")
                    
                    # Add timeout to prevent hanging requests
                    chunk_bars = await asyncio.wait_for(
                        self.rithmic_client.get_historical_time_bars(
                            contract,
                            self.status.current_exchange,
                            chunk_start,
                            chunk_end,
                            bar_type,
                            1
                        ),
                        timeout=60.0  # 60 second timeout per chunk
                    )
                    
                    # Update progress in UI
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 1.0,
                            'status': 'complete'
                        }
                    
                    return chunk_bars
                    
                except asyncio.TimeoutError:
                    failed_chunks += 1
                    logger.error(f"Timeout downloading chunk {chunk_idx+1}/{len(time_chunks)} for {contract}")
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 0,
                            'status': 'timeout'
                        }
                    return []
                    
                except Exception as e:
                    failed_chunks += 1
                    logger.error(f"Error downloading chunk {chunk_idx+1}/{len(time_chunks)} for {contract}: {e}")
                    if hasattr(self, 'status') and hasattr(self.status, 'download_progress'):
                        self.status.download_progress[chunk_id] = {
                            'progress': 0,
                            'status': 'error'
                        }
                    return []
        
        # Create tasks for all chunks
        tasks = [process_chunk(i, chunk[0], chunk[1]) for i, chunk in enumerate(time_chunks)]
        
        # Wait for all tasks to complete and gather results
        chunk_results = await asyncio.gather(*tasks)
        
        # Combine all results
        for chunk_bars in chunk_results:
            if chunk_bars:
                all_bars.extend(chunk_bars)
                total_bars += len(chunk_bars)
        
        # Calculate performance metrics
        download_duration = (datetime.now() - download_start_time).total_seconds()
        bars_per_second = total_bars / max(1, download_duration)
        
        logger.info(f"Downloaded {total_bars} {data_type} bars in {download_duration:.2f}s ({bars_per_second:.2f} bars/s)")
        logger.info(f"Failed chunks: {failed_chunks}/{len(time_chunks)}")
        
        # Save to database with batching for better performance
        if all_bars:
            # Process in batches of 5000 records for better database performance
            batch_size = 5000
            data_records = []
            
            for bar in all_bars:
                try:
                    record = {
                        'timestamp': bar.get('bar_end_datetime', datetime.now()),
                        'symbol': symbol,
                        'contract': contract,
                        'exchange': self.status.current_exchange,
                        'exchange_code': 'XCME' if self.status.current_exchange == 'CME' else self.status.current_exchange,
                        'open': float(bar.get('open', 0)),
                        'high': float(bar.get('high', 0)),
                        'low': float(bar.get('low', 0)),
                        'close': float(bar.get('close', 0)),
                        'volume': int(bar.get('volume', 0)),
                        'tick_count': int(bar.get('tick_count', 1)),
                        'vwap': float(bar.get('vwap', bar.get('close', 0))),
                        'bid': None,
                        'ask': None,
                        'spread': None,
                        'data_quality_score': 1.0,
                        'is_regular_hours': True
                    }
                    data_records.append(record)
                    
                    # Insert in batches to avoid memory issues with large datasets
                    if len(data_records) >= batch_size:
                        await helper.bulk_insert_market_data(data_records, table_name)
                        data_records = []
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing bar data: {e}, bar: {bar}")
            
            # Insert any remaining records
            if data_records:
                await helper.bulk_insert_market_data(data_records, table_name)
                
            logger.info(f"Inserted {total_bars} {data_type} bars into {table_name}")
    
    async def initialize_database(self):
        """Initialize database with progress tracking"""
        results = "## 🔧 Database Initialization\n\n"
        
        try:
            # Test connection
            db_manager = get_database_manager()
            connection_ok = await db_manager.test_connection()
            
            if not connection_ok:
                results += "❌ **Connection Test**: Failed\n"
                self.update_results(results)
                return
            
            results += "✅ **Connection Test**: Successful\n"
            
            # Initialize extensions
            try:
                await db_manager.initialize_database()
                results += "✅ **Extensions**: Initialized\n"
            except Exception as e:
                results += f"❌ **Extensions**: Error - {str(e)}\n"
                self.update_results(results)
                return
            
            # Verify tables
            try:
                tables_ok = await db_manager.verify_tables()
                if tables_ok:
                    results += "✅ **Tables**: Verified\n"
                else:
                    results += "⚠️ **Tables**: Some missing - attempting to create\n"
                    # Try to create tables
                    from shared.database.connection import test_database_setup
                    await test_database_setup()
                    results += "✅ **Tables**: Created successfully\n"
            except Exception as e:
                results += f"❌ **Tables**: Error - {str(e)}\n"
            
            # Test data insertion
            try:
                async with get_async_session() as session:
                    helper = TimescaleDBHelper(session)
                    
                    test_data = [{
                        'timestamp': pd.Timestamp.now(),
                        'symbol': 'TEST',
                        'contract': 'TESTINIT',
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
                    }]
                    
                    await helper.bulk_insert_market_data(test_data, 'market_data_seconds')
                    
                    # Clean up test data
                    from sqlalchemy import text
                    await session.execute(text("""
                        DELETE FROM market_data_seconds 
                        WHERE symbol = 'TEST' AND contract = 'TESTINIT'
                    """))
                    await session.commit()
                    
                    results += "✅ **Data Insertion**: Test successful\n"
                    
            except Exception as e:
                results += f"❌ **Data Insertion**: Error - {str(e)}\n"
            
            # Update connection status
            self.status.db_connected = True
            results += "\n**Status**: Database initialization completed successfully!"
            
        except Exception as e:
            results += f"❌ **Fatal Error**: {str(e)}\n"
        
        self.update_results(results)