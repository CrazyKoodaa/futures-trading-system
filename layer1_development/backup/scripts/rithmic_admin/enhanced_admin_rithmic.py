"""
Enhanced Rithmic Admin Tool - Main Application
Provides a modern TUI interface for Rithmic data management with live updates

This is the main entry point that coordinates all components:
- admin_core_classes.py: Core data structures and TUI components
- admin_operations.py: Business logic and Rithmic/DB operations  
- admin_keyboard_handler.py: Keyboard input and navigation
- admin_display_manager.py: Display rendering and management
- admin_config_utils.py: Configuration and utilities
"""

import asyncio
import logging
import logging.handlers
import sys
import os
import io
from datetime import datetime

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to import rich components
try:
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import our modular components
from layer1_development.scripts.rithmic_admin.admin_core_classes import SystemStatus, TUIComponents, KEYBOARD_AVAILABLE
from layer1_development.scripts.rithmic_admin.admin_operations import AdminOperations
from layer1_development.scripts.rithmic_admin.admin_keyboard_handler import KeyboardHandler, SimpleInputHandler
from layer1_development.scripts.rithmic_admin.admin_display_manager import DisplayManager, ProgressTracker
from layer1_development.scripts.rithmic_admin.admin_config_utils import (
    get_admin_config, get_error_handler, get_session_manager, 
    get_performance_monitor, TimedOperation
)

# Custom logging handler to capture logs for the UI
class UILogHandler(logging.Handler):
    def __init__(self, status):
        super().__init__()
        self.status = status
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.status.add_log_message(msg)
        except Exception:
            self.handleError(record)

# Configure logging
import sys
import io
import os
import platform
from logging.handlers import RotatingFileHandler, NTEventLogHandler

# Create a minimal console handler that only shows critical information
class MinimalConsoleHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)
        
    def emit(self, record):
        # Only emit if this is a critical message or an explicit UI message
        if record.levelno >= logging.CRITICAL or getattr(record, 'ui_message', False):
            try:
                msg = self.format(record)
                stream = self.stream
                # Replace unsupported characters with their ASCII equivalents
                msg = msg.replace('🚀', 'LAUNCH').replace('✅', 'OK').replace('❌', 'X')
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)

# Create a UI logger filter to mark messages that should be shown in the console
class UIMessageFilter(logging.Filter):
    def filter(self, record):
        # Check if this is a UI message (we'll set this attribute when logging UI messages)
        if getattr(record, 'ui_message', False):
            return True
        # For non-UI messages, only allow ERROR and above to console
        return record.levelno >= logging.ERROR

# Ensure log directory exists (as a hidden directory)
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".logs")
os.makedirs(log_dir, exist_ok=True)

# Try to make the directory hidden on Windows
if platform.system() == 'Windows':
    try:
        import ctypes
        # Convert to absolute path to ensure it works correctly
        abs_log_dir = os.path.abspath(log_dir)
        # 2 = Hidden attribute
        ctypes.windll.kernel32.SetFileAttributesW(abs_log_dir, 2)
    except Exception as e:
        # Log the error but continue
        print(f"Note: Could not set log directory as hidden: {e}")
        
# Create a .gitignore file in the log directory to prevent logs from being committed
gitignore_path = os.path.join(log_dir, ".gitignore")
if not os.path.exists(gitignore_path):
    try:
        with open(gitignore_path, 'w') as f:
            f.write("# Ignore all log files\n")
            f.write("*\n")
            f.write("!.gitignore\n")
    except Exception:
        pass  # Ignore if we can't create the .gitignore file

log_file = os.path.join(log_dir, "rithmic_admin.log")

# Configure root logger to capture all logs
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # Capture all levels

# Remove any existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Create formatters
detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
console_formatter = logging.Formatter('%(message)s')  # Simplified console output

# File handler with rotation (10MB max size, keep 5 backup files)
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)  # Log everything to file
file_handler.setFormatter(detailed_formatter)

# Console handler (minimal)
console_handler = MinimalConsoleHandler()
console_handler.setLevel(logging.ERROR)  # Only ERROR and above to console by default
console_handler.setFormatter(console_formatter)
console_handler.addFilter(UIMessageFilter())

# Try to add Windows Event Log handler if on Windows
try:
    if platform.system() == 'Windows':
        event_handler = NTEventLogHandler("Rithmic Admin Tool")
        event_handler.setLevel(logging.WARNING)  # Only warnings and above to event log
        event_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(event_handler)
except Exception:
    # If event log handler fails, just continue without it
    pass

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Get our specific logger
logger = logging.getLogger("rithmic_admin")

# Helper function to log UI messages (that should appear in console)
def log_ui(message, level=logging.INFO):
    """Log a message that should appear in the UI/console"""
    record = logging.LogRecord(
        name="rithmic_admin.ui",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.ui_message = True
    console_handler.handle(record)
    
    # Also log to file with regular logger
    logger.log(level, message)

class RithmicAdminTUI:
    """Main TUI application for Rithmic Admin Tool"""
    
    def __init__(self):
        # Core components
        self.status = SystemStatus()
        self.config = get_admin_config()
        self.session = get_session_manager()
        self.error_handler = get_error_handler()
        self.performance_monitor = get_performance_monitor()
        
        # Set up custom log handler to capture logs for UI display
        self.log_handler = UILogHandler(self.status)
        self.log_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(self.log_handler)
        
        # Initialize from session
        self.status.current_exchange = self.session.get_last_exchange()
        self.status.current_symbols = self.session.get_last_symbols()
        
        # UI components
        self.tui = TUIComponents(self.status)
        self.progress_tracker = ProgressTracker()
        
        # Menu configuration
        self.menu_items = [
            "Test Connections (DB + Rithmic)",
            "Search Symbols & Check Contracts", 
            "Download Historical Data",
            "View TimescaleDB Data",
            "Initialize/Setup Database",
            "Exit"
        ]
        
        # State management
        self.running = True
        self.current_menu_item = 0
        self.results_content = ""
        self.show_results = False
        
        # Display and input handlers
        self.display_manager = DisplayManager(self.status, self.tui)
        
        # Initialize operations with enhanced callbacks and display manager
        self.operations = AdminOperations(self.status, self.update_results_with_tracking, self.display_manager)
        
        # Setup input handling based on availability
        if KEYBOARD_AVAILABLE:
            self.input_handler = KeyboardHandler(len(self.menu_items))
            self.setup_keyboard_callbacks()
        else:
            self.input_handler = SimpleInputHandler(len(self.menu_items))
        
        # Setup error recovery strategies
        self.setup_error_recovery()
        
        # Add initial log message
        self.status.add_log_message("Enhanced Rithmic Admin Tool initialized")
        logger.info("Enhanced Rithmic Admin Tool initialized")
    
    def setup_keyboard_callbacks(self):
        """Setup keyboard handler callbacks"""
        if isinstance(self.input_handler, KeyboardHandler):
            # Set the menu change callback (already synchronous)
            self.input_handler.set_menu_change_callback(self.on_menu_change)
            
            # Create synchronous wrappers for async callbacks
            def execute_wrapper(item: int) -> None:
                asyncio.create_task(self.on_menu_execute(item))
                return None
                
            def shutdown_wrapper() -> None:
                asyncio.create_task(self.on_shutdown_request())
                return None
                
            # Set the callbacks with proper return types
            self.input_handler.set_menu_execute_callback(execute_wrapper)
            self.input_handler.set_shutdown_callback(shutdown_wrapper)
    
    def setup_error_recovery(self):
        """Setup error recovery strategies"""
        self.error_handler.register_recovery_strategy(
            'ConnectionError', 
            self.recover_connection_error
        )
        self.error_handler.register_recovery_strategy(
            'TimeoutError',
            self.recover_timeout_error
        )
    
    async def recover_connection_error(self, error, context):
        """
        Enhanced recovery strategy for connection errors with progressive backoff
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        error_type = type(error).__name__
        error_msg = str(error)
        logger.info(f"Attempting to recover from connection error: {error_type} - {error_msg}")
        self.status.add_log_message(f"Connection issue detected. Attempting recovery...")
        
        # Progressive backoff for retries
        max_retries = 3
        base_delay = 2  # seconds
        
        for retry in range(max_retries):
            try:
                # Calculate backoff delay with jitter to avoid thundering herd
                delay = base_delay * (2 ** retry) * (0.5 + 0.5 * (asyncio.get_event_loop().time() % 1))
                
                # Log retry attempt
                logger.info(f"Recovery attempt {retry+1}/{max_retries} after {delay:.2f}s delay")
                self.status.add_log_message(f"Recovery attempt {retry+1}/{max_retries}...")
                
                # Wait before retry
                await asyncio.sleep(delay)
                
                if "rithmic" in context.lower():
                    # Check if it's a specific Rithmic error that requires special handling
                    if "authentication" in error_msg.lower() or "login" in error_msg.lower():
                        logger.warning("Authentication issue detected. Attempting full reconnection...")
                        # Force disconnect first to clean up any lingering connections
                        await self.operations.disconnect_from_rithmic(timeout=5.0)
                        await asyncio.sleep(1)  # Give it a moment to fully disconnect
                    
        Enhanced recovery strategy for connection errors with progressive backoff
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        Enhanced recovery strategy for connection errors with progressive backoff
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        error_type = type(error).__name__
        error_msg = str(error)
        logger.info(f"Attempting to recover from connection error: {error_type} - {error_msg}")
        self.status.add_log_message(f"Connection issue detected. Attempting recovery...")
        
        # Progressive backoff for retries
        max_retries = 3
        base_delay = 2  # seconds
        
        for retry in range(max_retries):
            try:
                # Calculate backoff delay with jitter to avoid thundering herd
                delay = base_delay * (2 ** retry) * (0.5 + 0.5 * (asyncio.get_event_loop().time() % 1))
                
                # Log retry attempt
                logger.info(f"Recovery attempt {retry+1}/{max_retries} after {delay:.2f}s delay")
                self.status.add_log_message(f"Recovery attempt {retry+1}/{max_retries}...")
                
                # Wait before retry
                await asyncio.sleep(delay)
                
                if "rithmic" in context.lower():
                    # Check if it's a specific Rithmic error that requires special handling
                    if "authentication" in error_msg.lower() or "login" in error_msg.lower():
                        logger.warning("Authentication issue detected. Attempting full reconnection...")
                        # Force disconnect first to clean up any lingering connections
                        await self.operations.disconnect_from_rithmic(timeout=5.0)
                        await asyncio.sleep(1)  # Give it a moment to fully disconnect
                    
                    # Attempt to reconnect to Rithmic
                    connection_result = await self.operations.connect_to_rithmic()
                    
                    if connection_result:
                        logger.info("Rithmic connection recovery successful")
                        self.status.add_log_message("✅ Rithmic connection restored")
                        return True
                    
                elif "database" in context.lower():
                    # Test database connection with timeout
                    from shared.database.connection import get_database_manager
                    db_manager = get_database_manager()
                    
                    # Use wait_for to prevent hanging
                    try:
                        db_connection_result = await asyncio.wait_for(
                            db_manager.test_connection(),
                            timeout=10.0
                        )
                        
                        if db_connection_result:
                            logger.info("Database connection recovery successful")
                            self.status.add_log_message("✅ Database connection restored")
                            return True
                            
                    except asyncio.TimeoutError:
                        logger.error("Database connection test timed out")
                        self.status.add_log_message("⚠️ Database connection test timed out")
                
            except Exception as e:
                logger.error(f"Recovery attempt {retry+1} failed: {type(e).__name__} - {e}")
                self.status.add_log_message(f"Recovery attempt failed: {type(e).__name__}")
        
        # If we get here, all retries failed
        logger.error(f"Connection recovery failed after {max_retries} attempts")
        self.status.add_log_message(f"❌ Connection recovery failed after {max_retries} attempts")
        return False
    
    async def recover_timeout_error(self, error, context):
        """
        Enhanced recovery strategy for timeout errors with context-aware handling
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        logger.info(f"Attempting to recover from timeout error in context: {context}")
        self.status.add_log_message(f"Operation timed out. Attempting recovery...")
        
        # Different recovery strategies based on context
        if "historical_data" in context.lower() or "download" in context.lower():
            # For historical data timeouts, we might need to reduce the chunk size
            logger.info("Historical data timeout detected. Suggesting smaller chunk size.")
            self.status.add_log_message("⚠️ Historical data timeout. Try reducing the date range.")
            
            # Wait longer for historical data operations
            await asyncio.sleep(5)
            return True
            
        elif "connection" in context.lower():
            # For connection timeouts, we need a more aggressive recovery
            logger.info("Connection timeout detected. Attempting reconnection.")
            
            # For connection timeouts, delegate to the connection error recovery
            return await self.recover_connection_error(error, context)
            
        else:
            # Generic timeout recovery
            logger.info("Generic timeout detected. Waiting before retry.")
            self.status.add_log_message("⏱️ Operation timed out. Waiting before retry...")
            
            # Wait a bit and retry
            await asyncio.sleep(3)
            return True
    
    def on_menu_change(self, menu_item: int):
        """Callback for menu item changes"""
        self.current_menu_item = menu_item
        self.display_manager.update_menu_selection(menu_item)
    
    async def on_menu_execute(self, menu_item: int):
        """Callback for menu item execution - non-blocking"""
        # Create a task to execute the menu item in the background
        # This allows the UI to remain responsive while the operation is running
        asyncio.create_task(self._execute_menu_item_with_timing(menu_item))
        
    async def _execute_menu_item_with_timing(self, menu_item: int):
        """
        Execute menu item with enhanced performance monitoring and metrics
        
        This method tracks execution time, memory usage, and other performance
        metrics for menu operations to help identify bottlenecks.
        
        Args:
            menu_item: Index of the menu item to execute
        """
        # Get menu item name for better logging
        menu_name = self.menu_items[menu_item] if menu_item < len(self.menu_items) else f"Unknown-{menu_item}"
        
        # Create performance context for structured logging
        perf_context = {
            'operation': f'menu_item_{menu_item}',
            'operation_name': menu_name
        }
        
        # Try to get memory usage before operation
        try:
            import psutil
            process = psutil.Process()
            mem_before = process.memory_info().rss / (1024 * 1024)  # MB
            perf_context['memory_before_mb'] = mem_before
        except (ImportError, AttributeError):
            mem_before = None
        
        # Use the TimedOperation context manager with enhanced metrics
        with TimedOperation(self.performance_monitor, f"menu_item_{menu_item}", context=perf_context):
            try:
                # Execute the menu item
                await self.execute_menu_item(menu_item)
                
                # Get memory usage after operation if available
                if mem_before is not None:
                    try:
                        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
                        mem_diff = mem_after - mem_before
                        
                        # Log significant memory changes
                        if abs(mem_diff) > 10:  # More than 10MB change
                            logger.info(f"Memory change during '{menu_name}': {mem_diff:.2f}MB")
                            
                            # Add to UI log if memory usage is concerning
                            if mem_diff > 50:  # More than 50MB increase
                                self.status.add_log_message(
                                    f"⚠️ High memory usage detected: {mem_diff:.2f}MB increase"
                                )
                    except (NameError, AttributeError):
                        pass
                
            except Exception as e:
                # Log the error with the operation context
                logger.error(
                    f"Error executing '{menu_name}': {type(e).__name__} - {str(e)}",
                    extra=perf_context
                )
                # Re-raise for proper handling
                raise
        error_type = type(error).__name__
        error_msg = str(error)
        logger.info(f"Attempting to recover from connection error: {error_type} - {error_msg}")
        self.status.add_log_message(f"Connection issue detected. Attempting recovery...")
        
        # Progressive backoff for retries
        max_retries = 3
        base_delay = 2  # seconds
        
        for retry in range(max_retries):
            try:
                # Calculate backoff delay with jitter to avoid thundering herd
                delay = base_delay * (2 ** retry) * (0.5 + 0.5 * (asyncio.get_event_loop().time() % 1))
                
                # Log retry attempt
                logger.info(f"Recovery attempt {retry+1}/{max_retries} after {delay:.2f}s delay")
                self.status.add_log_message(f"Recovery attempt {retry+1}/{max_retries}...")
                
                # Wait before retry
                await asyncio.sleep(delay)
                
                if "rithmic" in context.lower():
                    # Check if it's a specific Rithmic error that requires special handling
                    if "authentication" in error_msg.lower() or "login" in error_msg.lower():
                        logger.warning("Authentication issue detected. Attempting full reconnection...")
                        # Force disconnect first to clean up any lingering connections
                        await self.operations.disconnect_from_rithmic(timeout=5.0)
                        await asyncio.sleep(1)  # Give it a moment to fully disconnect
                    
                    # Attempt to reconnect to Rithmic
                    connection_result = await self.operations.connect_to_rithmic()
                    
                    if connection_result:
                        logger.info("Rithmic connection recovery successful")
                        self.status.add_log_message("✅ Rithmic connection restored")
                        return True
                    
                elif "database" in context.lower():
                    # Test database connection with timeout
                    from shared.database.connection import get_database_manager
                    db_manager = get_database_manager()
                    
                    # Use wait_for to prevent hanging
                    try:
                        db_connection_result = await asyncio.wait_for(
                            db_manager.test_connection(),
                            timeout=10.0
                        )
                        
                        if db_connection_result:
                            logger.info("Database connection recovery successful")
                            self.status.add_log_message("✅ Database connection restored")
                            return True
                            
                    except asyncio.TimeoutError:
                        logger.error("Database connection test timed out")
                        self.status.add_log_message("⚠️ Database connection test timed out")
                
            except Exception as e:
                logger.error(f"Recovery attempt {retry+1} failed: {type(e).__name__} - {e}")
                self.status.add_log_message(f"Recovery attempt failed: {type(e).__name__}")
        
        # If we get here, all retries failed
        logger.error(f"Connection recovery failed after {max_retries} attempts")
        self.status.add_log_message(f"❌ Connection recovery failed after {max_retries} attempts")
        return False
    
    async def recover_timeout_error(self, error, context):
        """
        Enhanced recovery strategy for timeout errors with context-aware handling
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        logger.info(f"Attempting to recover from timeout error in context: {context}")
        self.status.add_log_message(f"Operation timed out. Attempting recovery...")
        
        # Different recovery strategies based on context
        if "historical_data" in context.lower() or "download" in context.lower():
            # For historical data timeouts, we might need to reduce the chunk size
            logger.info("Historical data timeout detected. Suggesting smaller chunk size.")
            self.status.add_log_message("⚠️ Historical data timeout. Try reducing the date range.")
            
            # Wait longer for historical data operations
            await asyncio.sleep(5)
            return True
            
        elif "connection" in context.lower():
            # For connection timeouts, we need a more aggressive recovery
            logger.info("Connection timeout detected. Attempting reconnection.")
            
            # For connection timeouts, delegate to the connection error recovery
            return await self.recover_connection_error(error, context)
            
        else:
            # Generic timeout recovery
            logger.info("Generic timeout detected. Waiting before retry.")
            self.status.add_log_message("⏱️ Operation timed out. Waiting before retry...")
            
            # Wait a bit and retry
            await asyncio.sleep(3)
            return True
    
    def on_menu_change(self, menu_item: int):
        """Callback for menu item changes"""
        self.current_menu_item = menu_item
        self.display_manager.update_menu_selection(menu_item)
    
    async def on_menu_execute(self, menu_item: int):
        """Callback for menu item execution - non-blocking"""
        # Create a task to execute the menu item in the background
        # This allows the UI to remain responsive while the operation is running
        asyncio.create_task(self._execute_menu_item_with_timing(menu_item))
        
    async def _execute_menu_item_with_timing(self, menu_item: int):
        """
        Execute menu item with enhanced performance monitoring and metrics
        
        This method tracks execution time, memory usage, and other performance
        metrics for menu operations to help identify bottlenecks.
        
        Args:
            menu_item: Index of the menu item to execute
        """
        # Get menu item name for better logging
        menu_name = self.menu_items[menu_item] if menu_item < len(self.menu_items) else f"Unknown-{menu_item}"
        
        # Create performance context for structured logging
        perf_context = {
            'operation': f'menu_item_{menu_item}',
            'operation_name': menu_name
        }
        
        # Try to get memory usage before operation
        try:
            import psutil
            process = psutil.Process()
            mem_before = process.memory_info().rss / (1024 * 1024)  # MB
            perf_context['memory_before_mb'] = mem_before
        except (ImportError, AttributeError):
            mem_before = None
        
        # Use the TimedOperation context manager with enhanced metrics
        with TimedOperation(self.performance_monitor, f"menu_item_{menu_item}", context=perf_context):
            try:
                # Execute the menu item
                await self.execute_menu_item(menu_item)
                
                # Get memory usage after operation if available
                if mem_before is not None:
                    try:
                        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
                        mem_diff = mem_after - mem_before
                        
                        # Log significant memory changes
                        if abs(mem_diff) > 10:  # More than 10MB change
                            logger.info(f"Memory change during '{menu_name}': {mem_diff:.2f}MB")
                            
                            # Add to UI log if memory usage is concerning
                            if mem_diff > 50:  # More than 50MB increase
                                self.status.add_log_message(
                                    f"⚠️ High memory usage detected: {mem_diff:.2f}MB increase"
                                )
                    except (NameError, AttributeError):
                        pass
                
            except Exception as e:
                # Log the error with the operation context
                logger.error(
                    f"Error executing '{menu_name}': {type(e).__name__} - {str(e)}",
                    extra=perf_context
                )
                # Re-raise for proper handling
                raise
                    # Attempt to reconnect to Rithmic
                    connection_result = await self.operations.connect_to_rithmic()
                    
                    if connection_result:
                        logger.info("Rithmic connection recovery successful")
                        self.status.add_log_message("✅ Rithmic connection restored")
                        return True
                    
                elif "database" in context.lower():
                    # Test database connection with timeout
                    from shared.database.connection import get_database_manager
                    db_manager = get_database_manager()
                    
                    # Use wait_for to prevent hanging
                    try:
                        db_connection_result = await asyncio.wait_for(
                            db_manager.test_connection(),
                            timeout=10.0
                        )
                        
                        if db_connection_result:
                            logger.info("Database connection recovery successful")
                            self.status.add_log_message("✅ Database connection restored")
                            return True
                            
                    except asyncio.TimeoutError:
                        logger.error("Database connection test timed out")
                        self.status.add_log_message("⚠️ Database connection test timed out")
                
            except Exception as e:
                logger.error(f"Recovery attempt {retry+1} failed: {type(e).__name__} - {e}")
                self.status.add_log_message(f"Recovery attempt failed: {type(e).__name__}")
        
        # If we get here, all retries failed
        logger.error(f"Connection recovery failed after {max_retries} attempts")
        self.status.add_log_message(f"❌ Connection recovery failed after {max_retries} attempts")
        return False
    
    async def recover_timeout_error(self, error, context):
        """
        Enhanced recovery strategy for timeout errors with context-aware handling
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        logger.info(f"Attempting to recover from timeout error in context: {context}")
        self.status.add_log_message(f"Operation timed out. Attempting recovery...")
        
        # Different recovery strategies based on context
        if "historical_data" in context.lower() or "download" in context.lower():
            # For historical data timeouts, we might need to reduce the chunk size
            logger.info("Historical data timeout detected. Suggesting smaller chunk size.")
            self.status.add_log_message("⚠️ Historical data timeout. Try reducing the date range.")
            
            # Wait longer for historical data operations
            await asyncio.sleep(5)
            return True
            
        elif "connection" in context.lower():
            # For connection timeouts, we need a more aggressive recovery
            logger.info("Connection timeout detected. Attempting reconnection.")
            
            # For connection timeouts, delegate to the connection error recovery
            return await self.recover_connection_error(error, context)
            
        else:
            # Generic timeout recovery
            logger.info("Generic timeout detected. Waiting before retry.")
            self.status.add_log_message("⏱️ Operation timed out. Waiting before retry...")
            
            # Wait a bit and retry
            await asyncio.sleep(3)
            return True
    
    def on_menu_change(self, menu_item: int):
        """Callback for menu item changes"""
        self.current_menu_item = menu_item
        self.display_manager.update_menu_selection(menu_item)
    
    async def on_menu_execute(self, menu_item: int):
        """Callback for menu item execution - non-blocking"""
        # Create a task to execute the menu item in the background
        # This allows the UI to remain responsive while the operation is running
        asyncio.create_task(self._execute_menu_item_with_timing(menu_item))
               
            # Add arguments to logging context
            log_context['args'] = vars(args)
            logger.debug(f"Command line arguments: {vars(args)}", extra=log_context)
            
        except (NameError, UnboundLocalError):
            # If args doesn't exist or is unbound, parse arguments
            args = parse_arguments()
            log_context['args'] = vars(args)
            logger.debug(f"Command line arguments (reparsed): {vars(args)}", extra=log_context)
        
        # Check system environment
        try:
            import platform
            import psutil
            
            # Collect system information for diagnostics
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_available': psutil.virtual_memory().available / (1024 * 1024),  # MB
                'memory_total': psutil.virtual_memory().total / (1024 * 1024)  # MB
            }
            
            log_context['system_info'] = system_info
            logger.info(f"System information: {system_info}", extra=log_context)
            
            # Check if system has enough resources
            if system_info['memory_available'] < 500:  # Less than 500MB available
                logger.warning("Low memory available. Performance may be affected.", extra=log_context)
                log_ui("⚠️ Low system memory detected. Performance may be affected.")
                
        except ImportError:
            logger.info("psutil not available. Skipping system diagnostics.", extra=log_context)
        
        # Check and report missing dependencies with more detailed information
        missing_deps = []
        optional_deps = []
        
        if not RICH_AVAILABLE:
            missing_deps.append(("rich", "Enhanced UI rendering"))
        if not KEYBOARD_AVAILABLE:
            missing_deps.append(("keyboard", "Keyboard navigation"))
            
        # Check for other optional dependencies
        try:
            import pandas
            log_context['pandas_version'] = pandas.__version__
        except ImportError:
            optional_deps.append(("pandas", "Data analysis capabilities"))
            
        try:
            import async_rithmic
            log_context['async_rithmic_version'] = async_rithmic.__version__
        except (ImportError, AttributeError):
            missing_deps.append(("async_rithmic", "Rithmic API connectivity"))
        
        # Log dependency information
        if missing_deps:
            missing_names = [f"{name} ({purpose})" for name, purpose in missing_deps]
            logger.warning(f"Required dependencies missing: {', '.join(missing_names)}", extra=log_context)
            log_ui(f"⚠️ Missing required dependencies: {', '.join(name for name, _ in missing_deps)}")
            log_ui(f"Install with: pip install {' '.join(name for name, _ in missing_deps)}")
            
        if optional_deps:
            optional_names = [f"{name} ({purpose})" for name, purpose in optional_deps]
            logger.info(f"Optional dependencies missing: {', '.join(optional_names)}", extra=log_context)
            log_ui(f"ℹ️ For full functionality: pip install {' '.join(name for name, _ in optional_deps)}")
        
        # Initialize application with configuration and performance monitoring
        logger.info("Initializing application", extra=log_context)
        app = RithmicAdminTUI()
        
        # Override display mode if --simple flag is used
        if args.simple:
            logger.info("Simple mode forced via command line", extra=log_context)
            app.config.set('display.mode', 'simple')
        
        # Run the application with performance tracking
        logger.info("Starting application main loop", extra=log_context)
        run_start_time = datetime.now()
        await app.run()
        run_duration = (datetime.now() - run_start_time).total_seconds()
        logger.info(f"Application main loop completed in {run_duration:.2f}s", extra=log_context)
        
    except KeyboardInterrupt:
        logger.info("Program terminated by user", extra=log_context)
        log_ui("Program terminated by user")
        
    except ImportError as e:
        # Special handling for import errors which are common setup issues
        module_name = getattr(e, 'name', str(e))
        logger.error(f"Missing module: {module_name}", extra=log_context)
        log_ui(f"❌ Missing required module: {module_name}", level=logging.ERROR)
        log_ui(f"Please install the missing module: pip install {module_name}", level=logging.ERROR)
        log_ui(f"Full error: {str(e)}", level=logging.ERROR)
        
    except ConnectionError as e:
        # Special handling for connection errors
        logger.error(f"Connection error: {str(e)}", extra=log_context)
        log_ui(f"❌ Connection error: {str(e)}", level=logging.ERROR)
        log_ui("Please check your network connection and Rithmic server status.", level=logging.ERROR)
        log_ui(f"See log file for details: {log_file}", level=logging.ERROR)
        
    except Exception as e:
        # Enhanced exception handling with more context
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Get traceback information
        import traceback
        tb_str = traceback.format_exc()
        
        # Add error details to log context
        log_context['error_type'] = error_type
        log_context['error_message'] = error_msg
        
        logger.exception(f"Unhandled {error_type}: {error_msg}", extra=log_context)
        
        # Provide more helpful error messages to the user
        log_ui(f"❌ Error ({error_type}): {error_msg}", level=logging.ERROR)
        log_ui(f"See log file for details: {log_file}", level=logging.ERROR)
        
        # For specific error types, provide more targeted help
        if "timeout" in error_msg.lower() or isinstance(e, asyncio.TimeoutError):
            log_ui("This may be due to network issues or Rithmic server load.", level=logging.ERROR)
            log_ui("Try again later or check your connection settings.", level=logging.ERROR)
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            log_ui("This may be due to permission issues or invalid credentials.", level=logging.ERROR)
            log_ui("Check your Rithmic credentials and permissions.", level=logging.ERROR)
    
    finally:
        # Log application shutdown with runtime statistics
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds()
        log_context['end_time'] = end_time.isoformat()
        log_context['runtime_seconds'] = runtime
        
        logger.info(f"Application shutdown complete. Total runtime: {runtime:.2f}s", extra=log_context 
    async def _execute_menu_item_with_timing(self, menu_item: int):
        """
        Execute menu item with enhanced performance monitoring and metrics
        
        This method tracks execution time, memory usage, and other performance
        metrics for menu operations to help identify bottlenecks.
        
        Args:
            menu_item: Index of the menu item to execute
        """
        # Get menu item name for better logging
        menu_name = self.menu_items[menu_item] if menu_item < len(self.menu_items) else f"Unknown-{menu_item}"
        
        # Create performance context for structured logging
        perf_context = {
            'operation': f'menu_item_{menu_item}',
            'operation_name': menu_name
        }
        
        # Try to get memory usage before operation
        try:
            import psutil
            process = psutil.Process()
            mem_before = process.memory_info().rss / (1024 * 1024)  # MB
            perf_context['memory_before_mb'] = mem_before
        except (ImportError, AttributeError):
            mem_before = None
        
        # Use the TimedOperation context manager with enhanced metrics
        with TimedOperation(self.performance_monitor, f"menu_item_{menu_item}", context=perf_context):
            try:
                # Execute the menu item
                await self.execute_menu_item(menu_item)
                
                # Get memory usage after operation if available
                if mem_before is not None:
                    try:
                        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
                        mem_diff = mem_after - mem_before
                        
                        # Log significant memory changes
                        if abs(mem_diff) > 10:  # More than 10MB change
                            logger.info(f"Memory change during '{menu_name}': {mem_diff:.2f}MB")
                            
                            # Add to UI log if memory usage is concerning
                            if mem_diff > 50:  # More than 50MB increase
                                self.status.add_log_message(
                                    f"⚠️ High memory usage detected: {mem_diff:.2f}MB increase"
                                )
                    except (NameError, AttributeError):
                        pass
                
            except Exception as e:
                # Log the error with the operation context
                logger.error(
                    f"Error executing '{menu_name}': {type(e).__name__} - {str(e)}",
                    extra=perf_context
                )
                # Re-raise for proper handling
                raise
    
    async def on_shutdown_request(self):
        """Callback for shutdown requests"""
        await self.shutdown()
    
    def update_results_with_tracking(self, content: str):
        """Enhanced results update with session tracking"""
        self.results_content = content
        self.show_results = True
        self.display_manager.update_results(content, True)
        
        # Also add to log panel for persistent visibility
        self.status.add_log_message(f"RESULT: {content[:100]}..." if len(content) > 100 else f"RESULT: {content}")
        
        # Log to session
        self.session.add_to_history("results_updated", {
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        })
    
    def update_progress(self, progress_data):
        """Update progress tracking"""
        self.status.download_progress = progress_data
        
        # Add significant progress updates to the log
        for key, progress in progress_data.items():
            # Only log when progress changes significantly (every 10%)
            progress_pct = progress.progress_percent
            if progress_pct % 10 < 1 and progress_pct > 0:  # Log at ~10%, ~20%, etc.
                self.status.add_log_message(
                    f"Progress: {progress.contract} {progress.data_type} - {progress_pct:.1f}% complete"
                )
            
            # Always log completion and errors
            if progress.completed_chunks >= progress.total_chunks:
                self.status.add_log_message(
                    f"✅ Completed: {progress.contract} {progress.data_type} - {progress.total_records} records"
                )
            elif progress.current_chunk_info.startswith("Error"):
                self.status.add_log_message(
                    f"❌ Error: {progress.contract} {progress.data_type} - {progress.current_chunk_info}"
                )
                
        # Progress will be automatically displayed by the TUI components
    
    async def execute_menu_item(self, item_index: int):
        """Execute the selected menu item with error handling"""
        try:
            menu_name = self.menu_items[item_index] if item_index < len(self.menu_items) else "Unknown"
            # Log to both logger and UI log panel
            self.status.add_log_message(f"Executing: {menu_name}")
            logger.info(f"Executing menu item: {menu_name}")
            
            # Update session
            self.session.add_to_history("menu_executed", {
                "item_index": item_index,
                "menu_name": menu_name
            })
            
            # Show a "working" message in the results panel
            self.update_results_with_tracking(f"Working on: {menu_name}...\n\nPlease wait while the operation completes.")
            
            # Execute the menu item in a background task to keep the UI responsive
            if item_index == 0:  # Test Connections
                # Create a background task for testing connections
                task = asyncio.create_task(self.operations.test_connections())
                # Add a callback to update the UI when the task completes
                task.add_done_callback(lambda t: self.status.add_log_message("Connection test completed"))
                
            elif item_index == 1:  # Search Symbols
                # Create a background task for searching symbols
                task = asyncio.create_task(self.operations.search_symbols_and_contracts())
                # Add a callback to update the session when the task completes
                def update_session(_):
                    self.session.update_symbols(self.status.current_symbols)
                    self.session.update_exchange(self.status.current_exchange)
                    self.status.add_log_message("Symbol search completed")
                task.add_done_callback(update_session)
                
            elif item_index == 2:  # Download Historical Data
                # Always use a fixed integer value for days
                days = 7  # Default to 7 days
                
                # Try to get from config if available
              
    Main entry point with enhanced dependency checking, error handling, and diagnostics
    """
    start_time = datetime.now()
    
    # Setup structured logging context
    log_context = {
        'session_id': f"session_{start_time.strftime('%Y%m%d_%H%M%S')}",
        'start_time': start_time.isoformat()
    }
    
    try:
        logger.info(f"Application starting", extra=log_context)
        
                    config_days = self.config.get('downloads.default_days')
                    if isinstance(config_days, (int, float, str)) and str(config_days).isdigit():
                        days = int(config_days)
                except (ValueError, TypeError, AttributeError):
                    logger.warning(f"Invalid days value in config: {self.config.get('downloads.default_days')}. Using default: 7")
                
                await self.operations.download_historical_data(days=days)
                
            elif item_index == 3:  # View Database Data
                await self.operations.view_database_data()
                
            elif item_index == 4:  # Initialize Database
                await self.operations.initialize_database()
                
            elif item_index == 5:  # Exit
                await self.shutdown()
                
        except Exception as e:
            # Use error handler for recovery
            recovery_success = await self.error_handler.handle_error(
                e, f"menu_item_{item_index}"
            )
            
            if not recovery_success:
                error_msg = f"❌ **Error executing menu item**: {str(e)}"
                self.update_results_with_tracking(error_msg)
            
            logger.exception(f"Error executing menu item {item_index}")
    
    async def shutdown(self):
        """Graceful shutdown with cleanup"""
        logger.info("Initiating graceful shutdown...")
        self.running = False
                
            # Add arguments to logging context
            log_context['args'] = vars(args)
            logger.debug(f"Command line arguments: {vars(args)}", extra=log_context)
            
        except (NameError, UnboundLocalError):
            # If args doesn't exist or is unbound, parse arguments
            args = parse_arguments()
            log_context['args'] = vars(args)
            logger.debug(f"Command line arguments (reparsed): {vars(args)}", extra=log_context)
        
        # Check system environment
        try:
            import platform
            import psutil
            
            # Collect system information for diagnostics
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_available': psutil.virtual_memory().available / (1024 * 1024),  # MB
                'memory_total': psutil.virtual_memory().total / (1024 * 1024)  # MB
            }
            
            log_context['system_info'] = system_info
            logger.info(f"System information: {system_info}", extra=log_context)
            
            # Check if system has enough resources
            if system_info['memory_available'] < 500:  # Less than 500MB available
                logger.warning("Low memory available. Performance may be affected.", extra=log_context)
                log_ui("⚠️ Low system memory detected. Performance may be affected.")
                
        except ImportError:
            logger.info("psutil not available. Skipping system diagnostics.", extra=log_context)
        
        # Check and report missing dependencies with more detailed information
        missing_deps = []
        optional_deps = []
        
        if not RICH_AVAILABLE:
            missing_deps.append(("rich", "Enhanced UI rendering"))
        if not KEYBOARD_AVAILABLE:
            missing_deps.append(("keyboard", "Keyboard navigation"))
            
        # Check for other optional dependencies
        try:
            import pandas
            log_context['pandas_version'] = pandas.__version__
        except ImportError:
            optional_deps.append(("pandas", "Data analysis capabilities"))
            
        try:
            import async_rithmic
            log_context['async_rithmic_version'] = async_rithmic.__version__
        except (ImportError, AttributeError):
            missing_deps.append(("async_rithmic", "Rithmic API connectivity"))
        
        # Log dependency information
        if missing_deps:
            missing_names = [f"{name} ({purpose})" for name, purpose in missing_deps]
            logger.warning(f"Required dependencies missing: {', '.join(missing_names)}", extra=log_context)
            log_ui(f"⚠️ Missing required dependencies: {', '.join(name for name, _ in missing_deps)}")
            log_ui(f"Install with: pip install {' '.join(name for name, _ in missing_deps)}")
            
        if optional_deps:
            optional_names = [f"{name} ({purpose})" for name, purpose in optional_deps]
            logger.info(f"Optional dependencies missing: {', '.join(optional_names)}", extra=log_context)
            log_ui(f"ℹ️ For full functionality: pip install {' '.join(name for name, _ in optional_deps)}")
        
        # Initialize application with configuration and performance monitoring
        logger.info("Initializing application", extra=log_context)
        app = RithmicAdminTUI()
        
        # Override display mode if --simple flag is used
        if args.simple:
            logger.info("Simple mode forced via command line", extra=log_context)
            app.config.set('display.mode', 'simple')
        
        # Run the application with performance tracking
        logger.info("Starting application main loop", extra=log_context)
        run_start_time = datetime.now()
        await app.run()
        run_duration = (datetime.now() - run_start_time).total_seconds()
        logger.info(f"Application main loop completed in {run_duration:.2f}s", extra=log_context)
        
    except KeyboardInterrupt:
        logger.info("Program terminated by user", extra=log_context)
        log_ui("Program terminated by user")
        
    except ImportError as e:
        # Special handling for import errors which are common setup issues
        module_name = getattr(e, 'name', str(e))
        logger.error(f"Missing module: {module_name}", extra=log_context)
        log_ui(f"❌ Missing required module: {module_name}", level=logging.ERROR)
        log_ui(f"Please install the missing module: pip install {module_name}", level=logging.ERROR)
        log_ui(f"Full error: {str(e)}", level=logging.ERROR)
        
    except ConnectionError as e:
        # Special handling for connection errors
        logger.error(f"Connection error: {str(e)}", extra=log_context)
        log_ui(f"❌ Connection error: {str(e)}", level=logging.ERROR)
        log_ui("Please check your network connection and Rithmic server status.", level=logging.ERROR)
        log_ui(f"See log file for details: {log_file}", level=logging.ERROR)
        
    except Exception as e:
        # Enhanced exception handling with more context
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Get traceback information
        import traceback
        tb_str = traceback.format_exc()
        
        # Add error details to log context
        log_context['error_type'] = error_type
        log_context['error_message'] = error_msg
        
        logger.exception(f"Unhandled {error_type}: {error_msg}", extra=log_context)
        
        # Provide more helpful error messages to the user
        log_ui(f"❌ Error ({error_type}): {error_msg}", level=logging.ERROR)
        log_ui(f"See log file for details: {log_file}", level=logging.ERROR)
        
        # For specific error types, provide more targeted help
        if "timeout" in error_msg.lower() or isinstance(e, asyncio.TimeoutError):
            log_ui("This may be due to network issues or Rithmic server load.", level=logging.ERROR)
            log_ui("Try again later or check your connection settings.", level=logging.ERROR)
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            log_ui("This may be due to permission issues or invalid credentials.", level=logging.ERROR)
            log_ui("Check your Rithmic credentials and permissions.", level=logging.ERROR)
    
    finally:
        # Log application shutdown with runtime statistics
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds()
        log_context['end_time'] = end_time.isoformat()
        log_context['runtime_seconds'] = runtime
        
        logger.info(f"Application shutdown complete. Total runtime: {runtime:.2f}s", extra=log_context
        try:
            # Save session data
            logger.debug("Saving session data...")
            try:
                self.session.save_session()
                logger.debug("Session data saved successfully")
            except Exception as e:
                logger.error(f"Error saving session data: {e}")
            
            # Shutdown display manager
            logger.debug("Shutting down display manager...")
            try:
                self.display_manager.shutdown()
                logger.debug("Display manager shutdown successfully")
            except Exception as e:
                logger.error(f"Error shutting down display manager: {e}")
            
            # Cleanup input handler
            logger.debug("Cleaning up input handler...")
            try:
                self.input_handler.cleanup()
                logger.debug("Input handler cleanup successful")
            except Exception as e:

                
                
                
                logger.error(f"Error cleaning up input handler: {e}")
            
            
            # Disconnect from Rithmic
            if self.operations.rithmic_client and self.status.rithmic_connected:
                logger.debug("Disconnecting from Rithmic...")
                try:
                    await self.operations.disconnect_from_rithmic()
                    logger.debug("Disconnected from Rithmic successfully")
                except Exception as e:
                    logger.error(f"Error disconnecting from Rithmic: {e}")
            
            # Log performance summary
            try:
                perf_summary = self.performance_monitor.get_performance_summary()
                logger.info(f"Performance summary: {perf_summary}")
            except Exception as e:
                logger.error(f"Error getting performance summary: {e}")
            
        except Exception as e:
            logger.exception(f"Unhandled error during shutdown: {e}")
        finally:
            logger.info("Application shutdown completed")
            log_ui("Application shutdown completed")
    
    async def run_with_keyboard_navigation(self):
        """Run with advanced keyboard navigation"""
        logger.info("Starting with keyboard navigation support")
        
        # Start display in background
        display_task = asyncio.create_task(
            self.display_manager.run_rich_display(self.menu_items)
        )
        
        try:
            # Main event loop
            while self.running:
                await asyncio.sleep(0.1)  # Small sleep to prevent CPU spinning
                
                # Process keyboard events from the queue
                if isinstance(self.input_handler, KeyboardHandler):
                    # Process any queued keyboard events
                    await self.input_handler.process_event_queue()
                    
                    # Update display with current state
                    self.display_manager.update_menu_selection(
                        self.input_handler.get_current_menu_item()
                    )
                
        except KeyboardInterrupt:
            await self.shutdown()
        finally:
            # Cancel display task
            if not display_task.done():
                display_task.cancel()
                try:
                    await display_task
                except asyncio.CancelledError:
                    pass
    
    def create_fallback_display(self):
        """Create a simple fallback display when Rich is not available"""
        # Clear the screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Display the simple menu
        self._display_simple_menu()
        
    def _display_simple_menu(self):
        """Display a simple text-based menu"""
        print("\n" + "=" * 50)
        print(" Rithmic Admin Tool ".center(50, "="))
        print("=" * 50)
        
        # Display status
        if hasattr(self.status, 'rithmic_connected'):
            rithmic_status = "✅ Connected" if self.status.rithmic_connected else "❌ Disconnected"
            print(f"Rithmic: {rithmic_status}")
        
        if hasattr(self.status, 'db_connected'):
            db_status = "✅ Connected" if self.status.db_connected else "❌ Disconnected"
            print(f"Database: {db_status}")
        
        print("-" * 50)
        
        # Display menu items
        for i, item in enumerate(self.menu_items[:-1]):
            print(f"{i+1}. {item}")
        
        # Exit option
        print(f"0. {self.menu_items[-1]}")
        print("-" * 50)
    
    async def run_with_simple_input(self):
        """Run with simple input handling"""
        logger.info("Starting with simple input mode")
        
        while self.running:
            try:
                # Simple text display for menu
                self._display_simple_menu()
                
                # Get user input using SimpleInputHandler
                if isinstance(self.input_handler, SimpleInputHandler):
                    choice = await self.input_handler.get_input()
                else:
                    # Fallback input method if we somehow don't have the right handler


                    try:

                        choice_str = input("\nEnter choice (1-5, 0=Exit): ").strip()

                        choice = int(choice_str) - 1 if choice_str.isdigit() and choice_str != "0" else len(self.menu_items) - 1



                    except (ValueError, EOFError, KeyboardInterrupt):

                        choice = None
                
                if choice is not None:
                    await self.execute_menu_item(choice)
                
            except KeyboardInterrupt:
                await self.shutdown()
                break
            except Exception as e:
                await self.error_handler.handle_error(e, "simple_input_loop")
                await asyncio.sleep(1)
    
    async def run(self):
        """Main run method with automatic mode detection"""
        try:
            # Display startup information
            startup_info = f"""
Enhanced Rithmic Admin Tool Starting

Configuration:
- Display Mode: {self.config.get('display.mode')}
- Keyboard Support: {KEYBOARD_AVAILABLE}
- Rich TUI: {RICH_AVAILABLE}
- Session: {self.session.get_session_info()}

Dependencies:
- Keyboard Navigation: {'OK' if KEYBOARD_AVAILABLE else 'X (install keyboard)'}
- Rich Display: {'OK' if RICH_AVAILABLE else 'X (install rich)'}
            """
            # Log to file
            logger.info(startup_info.strip())
            
            # Show minimal UI message
            log_ui("Enhanced Rithmic Admin Tool Starting...")
            
            # Choose run mode based on capabilities
            if RICH_AVAILABLE and KEYBOARD_AVAILABLE and self.config.get('display.mode') != 'simple':
                await self.run_with_keyboard_navigation()
            else:
                await self.run_with_simple_input()
                
        except Exception as e:
            logger.error(f"Application error: {e}")
            await self.error_handler.handle_error(e, "main_application")
        finally:
            await self.shutdown()

async def check_dependencies_and_run():
    """
    Main entry point with enhanced dependency checking, error handling, and diagnostics
    """
    start_time = datetime.now()
    
    # Setup structured logging context
    log_context = {
        'session_id': f"session_{start_time.strftime('%Y%m%d_%H%M%S')}",
        'start_time': start_time.isoformat()
    }
    
    try:
        logger.info(f"Application starting", extra=log_context)
        
        # Get command line arguments - use global args if available
        global args
        try:
            # Check if args exists in globals and is not None
            if 'args' in globals() and globals()['args'] is not None:
                pass  # Use the existing args
            else:
                args = parse_arguments()
                
            # Add arguments to logging context
            log_context['args'] = vars(args)
            logger.debug(f"Command line arguments: {vars(args)}", extra=log_context)
            
        except (NameError, UnboundLocalError):
            # If args doesn't exist or is unbound, parse arguments
            args = parse_arguments()
            log_context['args'] = vars(args)
            logger.debug(f"Command line arguments (reparsed): {vars(args)}", extra=log_context)
        
        # Check system environment
        try:
            import platform
            import psutil
            
            # Collect system information for diagnostics
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_available': psutil.virtual_memory().available / (1024 * 1024),  # MB
                'memory_total': psutil.virtual_memory().total / (1024 * 1024)  # MB
            }
            
            log_context['system_info'] = system_info
            logger.info(f"System information: {system_info}", extra=log_context)
            
            # Check if system has enough resources
            if system_info['memory_available'] < 500:  # Less than 500MB available
                logger.warning("Low memory available. Performance may be affected.", extra=log_context)
                log_ui("⚠️ Low system memory detected. Performance may be affected.")
                
        except ImportError:
            logger.info("psutil not available. Skipping system diagnostics.", extra=log_context)
        
        # Check and report missing dependencies with more detailed information
        missing_deps = []
        optional_deps = []
        
        if not RICH_AVAILABLE:
            missing_deps.append(("rich", "Enhanced UI rendering"))
        if not KEYBOARD_AVAILABLE:
            missing_deps.append(("keyboard", "Keyboard navigation"))
            
        # Check for other optional dependencies
        try:
            import pandas
            log_context['pandas_version'] = pandas.__version__
        except ImportError:
            optional_deps.append(("pandas", "Data analysis capabilities"))
            
        try:
            import async_rithmic
            log_context['async_rithmic_version'] = async_rithmic.__version__
        except (ImportError, AttributeError):
            missing_deps.append(("async_rithmic", "Rithmic API connectivity"))
        
        # Log dependency information
        if missing_deps:
            missing_names = [f"{name} ({purpose})" for name, purpose in missing_deps]
            logger.warning(f"Required dependencies missing: {', '.join(missing_names)}", extra=log_context)
            log_ui(f"⚠️ Missing required dependencies: {', '.join(name for name, _ in missing_deps)}")
            log_ui(f"Install with: pip install {' '.join(name for name, _ in missing_deps)}")
            
        if optional_deps:
            optional_names = [f"{name} ({purpose})" for name, purpose in optional_deps]
            logger.info(f"Optional dependencies missing: {', '.join(optional_names)}", extra=log_context)
            log_ui(f"ℹ️ For full functionality: pip install {' '.join(name for name, _ in optional_deps)}")
        
        # Initialize application with configuration and performance monitoring
        logger.info("Initializing application", extra=log_context)
        app = RithmicAdminTUI()
        
        # Override display mode if --simple flag is used
        if args.simple:
            logger.info("Simple mode forced via command line", extra=log_context)
            app.config.set('display.mode', 'simple')
        
        # Run the application with performance tracking
        logger.info("Starting application main loop", extra=log_context)
        run_start_time = datetime.now()
        await app.run()
        run_duration = (datetime.now() - run_start_time).total_seconds()
        logger.info(f"Application main loop completed in {run_duration:.2f}s", extra=log_context)
        
    except KeyboardInterrupt:
        logger.info("Program terminated by user", extra=log_context)
        log_ui("Program terminated by user")
        
    except ImportError as e:
        # Special handling for import errors which are common setup issues
        module_name = getattr(e, 'name', str(e))
        logger.error(f"Missing module: {module_name}", extra=log_context)
        log_ui(f"❌ Missing required module: {module_name}", level=logging.ERROR)
        log_ui(f"Please install the missing module: pip install {module_name}", level=logging.ERROR)
        log_ui(f"Full error: {str(e)}", level=logging.ERROR)
        
    except ConnectionError as e:
        # Special handling for connection errors
        logger.error(f"Connection error: {str(e)}", extra=log_context)
        log_ui(f"❌ Connection error: {str(e)}", level=logging.ERROR)
        log_ui("Please check your network connection and Rithmic server status.", level=logging.ERROR)
        log_ui(f"See log file for details: {log_file}", level=logging.ERROR)
        
    except Exception as e:
        # Enhanced exception handling with more context
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Get traceback information
        import traceback
        tb_str = traceback.format_exc()
        
        # Add error details to log context
        log_context['error_type'] = error_type
        log_context['error_message'] = error_msg
        
        logger.exception(f"Unhandled {error_type}: {error_msg}", extra=log_context)
        
        # Provide more helpful error messages to the user
        log_ui(f"❌ Error ({error_type}): {error_msg}", level=logging.ERROR)
        log_ui(f"See log file for details: {log_file}", level=logging.ERROR)
        
        # For specific error types, provide more targeted help
        if "timeout" in error_msg.lower() or isinstance(e, asyncio.TimeoutError):
            log_ui("This may be due to network issues or Rithmic server load.", level=logging.ERROR)
            log_ui("Try again later or check your connection settings.", level=logging.ERROR)
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            log_ui("This may be due to permission issues or invalid credentials.", level=logging.ERROR)
            log_ui("Check your Rithmic credentials and permissions.", level=logging.ERROR)
    
    finally:
        # Log application shutdown with runtime statistics
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds()
        log_context['end_time'] = end_time.isoformat()
        log_context['runtime_seconds'] = runtime
        
        logger.info(f"Application shutdown complete. Total runtime: {runtime:.2f}s", extra=log_context)

# Entry point setup
# Set up optimal event loop policy for Windows
if sys.platform.startswith('win'):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        pass  # Older Python versions
    
    async def run_live_display(self):
        """Run the live TUI display with smooth updates"""
        if not RICH_AVAILABLE:
            # Fallback to simple display
            logger.warning("Rich library not available, falling back to simple display")
            await self.run_simple_display()
            return
        
        # Rich TUI display with optimized rendering
        try:
            # Print a message to indicate we're starting the rich display
            print("Starting Rich terminal UI...")
            
            # Ensure the display manager has the menu items
            self.display_manager.menu_items = self.menu_items
            
            # Create a simple initial layout to show immediately
            initial_layout = self._create_quick_startup_layout()
            
            # Use Rich's Live display with the initial layout
            with Live(initial_layout, refresh_per_second=10, screen=True) as live:
                self.display_manager.live_display = live
                
                # Show the initial layout immediately
                live.update(initial_layout)
                
                # Set up keyboard input handling
                if KEYBOARD_AVAILABLE:
                    self.input_handler.start_listening(
                        on_up=lambda: self.on_menu_change(max(0, self.current_menu_item - 1)),
                        on_down=lambda: self.on_menu_change(min(len(self.menu_items) - 1, self.current_menu_item + 1)),
                        on_enter=lambda: asyncio.create_task(self.on_menu_execute(self.current_menu_item)),
                        on_exit=lambda: asyncio.create_task(self.on_shutdown_request())
                    )
                
                # Short delay to ensure the initial layout is displayed
                await asyncio.sleep(0.5)
                
                # After showing the initial layout, create the full layout
                # This allows the UI to appear immediately while the full layout is being prepared
                full_layout = self.tui.create_main_layout(
                    self.current_menu_item, 
                    self.menu_items, 
                    self.results_content, 
                    self.show_results
                )
                
                if full_layout is not None:
                    live.update(full_layout)
                
                # Main display loop
                while self.running:
                    try:
                        # Update layout using the display manager
                        layout = self.display_manager._create_rich_layout(self.menu_items)
                        if layout is not None:
                            live.update(layout)
                        
                        await asyncio.sleep(0.1)
                        
                    except KeyboardInterrupt:
                        await self.shutdown()
                        break
                    except Exception as e:
                        logger.error(f"Display error: {e}")
                        await asyncio.sleep(1)
                
                # Stop keyboard input handling
                if KEYBOARD_AVAILABLE:
                    self.input_handler.stop_listening()
                
        except Exception as e:
            logger.error(f"Live display failed: {e}")
            print(f"Rich display error: {e}")
            # Fall back to simple display
            await self.run_simple_display()
            
    def _create_quick_startup_layout(self):
        """Create a simple layout to show immediately during startup"""
        if not RICH_AVAILABLE:
            return None
            
        from rich.panel import Panel
        from rich.align import Align
        from rich.text import Text
        from rich.layout import Layout
        
        # Create a simple layout with just a title and loading message
        layout = Layout()
        
        layout.update(
            Panel(
                Align.center(
                    Text.from_markup(
                        "[bold cyan]RITHMIC DATA ADMIN TOOL[/bold cyan]\n\n"
                        "[green]Ready![/green]\n\n"
                        "Use arrow keys to navigate the menu.\n"
                        "Press Enter to select an option.\n\n"
                        "[yellow]Note:[/yellow] Connections to Rithmic will be established\n"
                        "only when you select the appropriate menu option."
                    ),
                    vertical="middle"
                ),
                title="Welcome",
                border_style="green"
            )
        )
        
        return layout
    
    async def run_simple_display(self):
        """Run simple text-based display"""
        while self.running:
            try:
                self.create_fallback_display()
                
                # Get user input
                try:
                    choice = input("\nEnter choice: ").strip()
                    
                    if choice.isdigit():
                        choice_num = int(choice)
                        if choice_num == 0:
                            choice_num = 5  # Map 0 to Exit
                        elif 1 <= choice_num <= 5:
                            choice_num -= 1  # Convert to 0-based index
                        else:
                            continue
                        
                        await self.execute_menu_item(choice_num)
                    
                except EOFError:
                    await self.shutdown()
                    break
                except KeyboardInterrupt:
                    await self.shutdown()
                    break
                    
            except Exception as e:
                logger.error(f"Simple display error: {e}")
                await asyncio.sleep(1)
    
    async def run(self):
        """Main run method"""
        logger.info("Starting Enhanced Rithmic Admin Tool")
        
        try:
            # Print a message to the console to indicate the app is starting
            print("Enhanced Rithmic Admin Tool Starting...")
            print("Initializing display...")
            
            # Ensure the display manager has the menu items
            self.display_manager.menu_items = self.menu_items
            
            # Set initial status message
            self.status.add_log_message("Starting application...")
            
            # Initialize application state (without connecting to services)
            await self.initialize_connections()
            
            # Choose the appropriate display mode and show UI immediately
            if RICH_AVAILABLE and KEYBOARD_AVAILABLE:
                logger.info("Using Rich TUI with keyboard navigation")
                await self.run_live_display()
            else:
                logger.info("Using simple text interface")
                await self.run_simple_display()
                    
        except Exception as e:
            logger.error(f"Application error: {e}")
            # Print the error to the console
            print(f"Error: {e}")
            # If there's an error, fall back to simple display
            try:
                await self.run_simple_display()
            except Exception as fallback_error:
                logger.error(f"Fallback display error: {fallback_error}")
        finally:
            await self.shutdown()
            
    async def initialize_connections(self):
        """Initialize application state without connecting to services"""
        try:
            # Just set the initial connection status without actually connecting
            self.status.rithmic_connected = False
            self.status.db_connected = False
            
            # Add a log message to indicate the application is ready
            self.status.add_log_message("Application initialized - select an option from the menu")
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            self.status.add_log_message(f"Initialization error: {e}")
            
        return True

async def main():
    """Main entry point"""
    logger.info("Application main() function started")
    print("Enhanced Rithmic Admin Tool Starting...")
    
    try:
        # Initialize the application
        app = RithmicAdminTUI()
        
        # Run the application
        await app.run()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        logger.info("Application terminated by user")
    except Exception as e:
        print(f"\nUnhandled exception: {e}")
        logger.exception(f"Unhandled exception in main(): {e}")
        
        # If there's a critical error, show a simple error message
        print("\n" + "=" * 50)
        print(" ERROR ".center(50, "="))
        print("=" * 50)
        print(f"The application encountered an error: {e}")
        print("\nCheck the logs for more details.")
        print("=" * 50)
    finally:
        logger.info("Application main() function completed")

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Rithmic Admin Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", type=str, help="Specify custom log file path")
    parser.add_argument("--simple", action="store_true", help="Force simple display mode")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output in console")
    parser.add_argument("--quiet", action="store_true", help="Minimize console output (default)")
    parser.add_argument("--show-log-path", action="store_true", help="Show log file path on startup")
    parser.add_argument("--help-extended", action="store_true", help="Show extended help information")
    
    args = parser.parse_args()
    
    # Show extended help if requested
    if args.help_extended:
        help_text = """
Enhanced Rithmic Admin Tool - Extended Help
===========================================

USAGE:
  python enhanced_admin_rithmic.py [OPTIONS]

OPTIONS:
  --debug           Enable detailed debug logging (useful for troubleshooting)
  --log-file PATH   Specify a custom log file location
  --simple          Force simple text-based interface (no Rich TUI)
  --verbose         Show verbose output in console (all log messages)
  --quiet           Minimize console output (default)
  --show-log-path   Show log file path on startup
  --help-extended   Show this extended help message

LOGGING:
  All application activity is logged to the '.logs/rithmic_admin.log' file
  Log files are rotated when they reach 10 MB, with 5 backup files kept
  Windows Event Log entries are created for warnings and errors

KEYBOARD SHORTCUTS (when using Rich TUI):
  Up/Down         Navigate menu items
  Enter           Select menu item
  Esc             Exit/Back
  Ctrl+C          Quit application

EXAMPLES:
  python enhanced_admin_rithmic.py --debug --log-file custom_log.txt
  python enhanced_admin_rithmic.py --simple --verbose
  python enhanced_admin_rithmic.py --quiet --show-log-path
"""
        print(help_text)
        sys.exit(0)
    
    return args

if __name__ == "__main__":
    # Parse command line arguments
    # Define args in global scope so it can be accessed by check_dependencies_and_run
    global args
    try:
        args = parse_arguments()
    except Exception as e:
        print(f"Error parsing arguments: {e}")
        sys.exit(1)
    
    # Set debug level if requested
    if args.debug:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        file_handler = root_logger.handlers[0]  # The file handler we created earlier
        file_handler.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled via command line")
    
    # Handle verbose/quiet console output
    if args.verbose:
        console_handler = root_logger.handlers[1]  # The console handler we created earlier
        console_handler.setLevel(logging.INFO)
        # Remove the UI filter to show all messages
        for filter in console_handler.filters:
            if isinstance(filter, UIMessageFilter):
                console_handler.removeFilter(filter)
        logger.debug("Verbose console output enabled")
        log_ui("Verbose console output enabled")
    elif args.quiet:
        # This is the default, but we'll set it explicitly
        console_handler = root_logger.handlers[1]
        console_handler.setLevel(logging.ERROR)
    
    # Use custom log file if specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'))
        file_handler.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        
        # Replace the existing file handler
        for i, handler in enumerate(root_logger.handlers):
            if isinstance(handler, (logging.FileHandler, logging.handlers.RotatingFileHandler)):
                root_logger.handlers[i] = file_handler
                break
        else:
            # If no existing file handler, add this one
            root_logger.addHandler(file_handler)
        
        logger.info(f"Using custom log file: {args.log_file}")
        if args.show_log_path:
            log_ui(f"Logging to: {args.log_file}")
    elif args.show_log_path:
        log_ui(f"Logging to: {log_file}")
    
    # Run the application
    logger.info("Starting application from command line")
    asyncio.run(check_dependencies_and_run())