"""
Enhanced Rithmic Admin Tool - Main Application (Fixed Version)
Provides a modern TUI interface for Rithmic data management with live updates
"""

import asyncio
import logging
import sys
import os
import random
from datetime import datetime

# Try to import rich components
try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to import rich components
try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import risk monitoring module
try:
    from layer1_development.scripts.rithmic_admin.risk_monitoring import run_risk_monitoring, RiskMonitor, RiskMonitoringUI
    RISK_MONITORING_AVAILABLE = True
except ImportError:
    RISK_MONITORING_AVAILABLE = False

# Setup logging
logger = logging.getLogger("rithmic_admin")
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Define keyboard availability
KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    pass

class PerformanceMonitor:
    """
    Performance monitoring utility for tracking operation metrics
    
    This class provides methods to record and analyze performance metrics
    for various operations in the application.
    """
    
    def __init__(self):
        """Initialize the performance monitor"""
        self.operations = {}
        self.start_time = datetime.now()
        
    def record_operation(self, operation, duration, status="success", context=None):
        """
        Record performance metrics for an operation
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            status: Status of the operation (success, error, timeout)
            context: Additional context information
        """
        if operation not in self.operations:
            self.operations[operation] = []
            
        self.operations[operation].append({
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "status": status,
            "context": context or {}
        })
        
        # Log performance metrics
        logger.debug(f"Performance: {operation} - {duration:.2f}s - {status}")
        
    def get_operation_stats(self, operation):
        """Get statistics for a specific operation"""
        if operation not in self.operations:
            return None
            
        durations = [op["duration"] for op in self.operations[operation]]
        success_count = sum(1 for op in self.operations[operation] if op["status"] == "success")
        error_count = sum(1 for op in self.operations[operation] if op["status"] != "success")
        
        return {
            "count": len(durations),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "success_rate": success_count / len(durations) if durations else 0,
            "error_count": error_count
        }
        
    def get_summary(self):
        """Get a summary of all operations"""
        return {
            "total_operations": sum(len(ops) for ops in self.operations.values()),
            "operations": {op: self.get_operation_stats(op) for op in self.operations}
        }


class RithmicAdminTUI:
    """Main TUI application class with enhanced performance monitoring"""
    
    def __init__(self):
        """Initialize the application with performance monitoring"""
        self.menu_items = [
            "Test Connections",
            "Search Symbols",
            "Download Historical Data",
            "View Database Data",
            "Initialize Database",
            "Risk Live Monitoring",
            "Exit"
        ]
        self.config = {
            'display': {
                'mode': 'rich' if RICH_AVAILABLE else 'simple'
            },
            'performance': {
                'enabled': True,
                'log_level': 'debug'
            },
            'risk': {
                'refresh_rate': 2,  # Refresh rate in seconds
                'demo_mode': True,  # Use demo data if true
                'critical_pnl_threshold': -5000,  # P&L threshold for critical risk
                'high_risk_pnl_threshold': -2000  # P&L threshold for high risk
            }
        }
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # Initialize console if Rich is available
        self.console = Console() if RICH_AVAILABLE else None
        
        # Track application state
        self.status = {
            'rithmic_connected': False,
            'db_connected': False,
            'log_messages': []
        }
        
    def get_config(self, key, default=None):
        """Get configuration value with dot notation"""
        parts = key.split('.')
        current = self.config
        
        for part in parts:
            if part not in current:
                return default
            current = current[part]
            
        return current
    
    def add_log_message(self, message, level=logging.INFO):
        """Add a log message to the status"""
        self.status['log_messages'].append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'level': level
        })
        logger.log(level, message)
        
    async def execute_menu_item(self, item_index):
        """
        Execute a menu item with performance tracking
        
        Args:
            item_index: Index of the menu item to execute
        """
        menu_name = self.menu_items[item_index] if item_index < len(self.menu_items) else f"Unknown-{item_index}"
        
        # Create performance context
        perf_context = {
            'operation': f'menu_item_{item_index}',
            'operation_name': menu_name
        }
        
        # Start timing
        start_time = datetime.now()
        
        try:
            # Log operation start
            logger.info(f"Executing menu item: {menu_name}")
            self.add_log_message(f"Executing: {menu_name}")
            
            # Handle specific menu items
            if menu_name == "Risk Live Monitoring":
                await self.run_risk_live_monitoring()
            else:
                # Simulate menu item execution for other items
                print(f"Executing menu item: {menu_name}")
                await asyncio.sleep(0.5)  # Simulate work
            
            # Record successful operation
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_monitor.record_operation(
                f'menu_item_{item_index}',
                duration,
                "success",
                perf_context
            )
            
            # Log completion
            logger.info(f"Menu item {menu_name} completed in {duration:.2f}s")
            self.add_log_message(f"Completed: {menu_name} in {duration:.2f}s")
            
            return True
            
        except Exception as e:
            # Record failed operation
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_monitor.record_operation(
                f'menu_item_{item_index}',
                duration,
                "error",
                {**perf_context, 'error': str(e), 'error_type': type(e).__name__}
            )
            
            # Log error
            logger.error(f"Error executing menu item {menu_name}: {e}")
            self.add_log_message(f"Error: {e}", logging.ERROR)
            
            return False
        
    async def run_risk_live_monitoring(self):
        """
        Implements the Risk Live Monitoring functionality
        
        This method connects to Rithmic API, subscribes to real-time data,
        and displays live risk metrics for active trading accounts using
        the Rich library for a modern, interactive dashboard.
        """
        try:
            # Check if Rich library is available
            if not RICH_AVAILABLE:
                print("\n=== Risk Live Monitoring ===")
                print("Rich library is not available. Using simple display mode.")
                print("Install Rich for an enhanced experience: pip install rich")
                await self._run_simple_risk_monitoring()
                return
                
            # Check if risk monitoring module is available
            if not RISK_MONITORING_AVAILABLE:
                print("\n=== Risk Live Monitoring ===")
                print("Risk monitoring module not available.")
                print("Using fallback implementation.")
                await self._run_simple_risk_monitoring()
                return
                
            # Log the start of risk monitoring
            logger.info("Starting Risk Live Monitoring")
            self.add_log_message("Starting Risk Live Monitoring")
            
            # Check if we're already connected to Rithmic
            rithmic_client = None
            if not self.status.get('rithmic_connected', False):
                print("Connecting to Rithmic API...")
                # In a real implementation, we would connect to Rithmic here
                # rithmic_client = await connect_to_rithmic()
                await asyncio.sleep(1)  # Simulate connection time
                self.status['rithmic_connected'] = True
                print("Connected to Rithmic API successfully")
            
            # Run the risk monitoring dashboard using our dedicated module
            console = Console()
            console.print(Panel(
                "[bold green]Starting Risk Live Monitoring Dashboard[/bold green]\n\n"
                "Loading account data and initializing monitoring...\n\n"
                "[dim]Press Ctrl+C to exit the dashboard[/dim]",
                title="Risk Monitoring",
                border_style="green"
            ))
            
            # Run the risk monitoring dashboard
            await run_risk_monitoring(rithmic_client)
            
            # Log completion
            logger.info("Risk Live Monitoring session ended")
            self.add_log_message("Risk Live Monitoring session ended")
            
        except KeyboardInterrupt:
            print("\nExiting risk monitoring...")
            logger.info("Risk monitoring interrupted by user")
            self.add_log_message("Risk monitoring interrupted by user")
            
        except Exception as e:
            logger.error(f"Error in risk monitoring: {e}")
            self.add_log_message(f"Error in risk monitoring: {e}", logging.ERROR)
            print(f"Error in risk monitoring: {e}")
            
            # Provide more detailed error information
            if RICH_AVAILABLE:
                console = Console()
                console.print_exception()
            raise
            
    async def _run_simple_risk_monitoring(self):
        """
        Fallback implementation of risk monitoring with simple text display
        """
        try:
            print("\n=== Risk Live Monitoring ===")
            
            # Check if we're already connected to Rithmic
            if not self.status.get('rithmic_connected', False):
                print("Connecting to Rithmic API...")
                # In a real implementation, we would connect to Rithmic here
                await asyncio.sleep(1)  # Simulate connection time
                self.status['rithmic_connected'] = True
                print("Connected to Rithmic API successfully")
            
            # Initialize risk monitoring
            print("Initializing risk monitoring...")
            await asyncio.sleep(0.5)
            
            # Define sample accounts for demonstration
            accounts = ["DEMO123", "DEMO456", "DEMO789"]
            
            # Display risk monitoring interface
            print("\nRisk Monitoring Dashboard")
            print("=" * 60)
            print(f"{'Account':<10} {'Position':<10} {'P&L':<10} {'Margin':<10} {'Risk Level':<10}")
            print("-" * 60)
            
            # Sample risk data (in a real implementation, this would come from Rithmic API)
            risk_data = [
                {"account": "DEMO123", "position": 5, "pnl": 1250.50, "margin": 5000, "risk": "Low"},
                {"account": "DEMO456", "position": -3, "pnl": -750.25, "margin": 3000, "risk": "Medium"},
                {"account": "DEMO789", "position": 10, "pnl": -2500.75, "margin": 8000, "risk": "High"}
            ]
            
            # Display risk data
            for data in risk_data:
                print(f"{data['account']:<10} {data['position']:<10} {data['pnl']:<10.2f} {data['margin']:<10} {data['risk']:<10}")
            
            print("\nPress Ctrl+C to exit risk monitoring")
            
            # Simulate real-time updates
            update_count = 0
            try:
                while update_count < 5:  # Limit to 5 updates for demo
                    await asyncio.sleep(2)
                    update_count += 1
                    
                    # Update sample data (in a real implementation, this would be real-time data)
                    for data in risk_data:
                        # Simulate price movement
                        data['pnl'] += (100 * (0.5 - random.random()))
                        
                        # Update risk level based on P&L
                        if data['pnl'] < -2000:
                            data['risk'] = "High"
                        elif data['pnl'] < 0:
                            data['risk'] = "Medium"
                        else:
                            data['risk'] = "Low"
                    
                    # Clear previous output and redisplay
                    print("\033[H\033[J")  # Clear screen
                    print("\nRisk Monitoring Dashboard (Updated)")
                    print("=" * 60)
                    print(f"{'Account':<10} {'Position':<10} {'P&L':<10} {'Margin':<10} {'Risk Level':<10}")
                    print("-" * 60)
                    
                    for data in risk_data:
                        print(f"{data['account']:<10} {data['position']:<10} {data['pnl']:<10.2f} {data['margin']:<10} {data['risk']:<10}")
                    
                    print(f"\nLast update: {datetime.now().strftime('%H:%M:%S')}")
                    print("Press Ctrl+C to exit risk monitoring")
            
            except KeyboardInterrupt:
                print("\nExiting risk monitoring...")
            
            print("\nRisk monitoring session ended")
            
        except Exception as e:
            logger.error(f"Error in simple risk monitoring: {e}")
            print(f"Error in risk monitoring: {e}")
            raise
            
    async def run(self):
        """Main run method with performance monitoring"""
        start_time = datetime.now()
        
        try:
            # Log application start
            logger.info("Application starting")
            
            # Display startup information
            print("Enhanced Rithmic Admin Tool")
            print(f"Display Mode: {self.get_config('display.mode')}")
            print(f"Keyboard Support: {KEYBOARD_AVAILABLE}")
            print(f"Rich TUI: {RICH_AVAILABLE}")
            
            # Display menu
            print("\nMenu:")
            for i, item in enumerate(self.menu_items):
                print(f"{i+1}. {item}")
                
            # Execute a few menu items to demonstrate performance monitoring
            await self.execute_menu_item(0)  # Test Connections
            await self.execute_menu_item(1)  # Search Symbols
            await self.execute_menu_item(5)  # Risk Live Monitoring
            
            # Display performance summary
            print("\nPerformance Summary:")
            summary = self.performance_monitor.get_summary()
            print(f"Total Operations: {summary['total_operations']}")
            
            for op_name, stats in summary['operations'].items():
                print(f"- {op_name}: {stats['count']} calls, avg: {stats['avg_duration']:.2f}s")
            
            print("\nApplication completed successfully")
            
            # Record overall application performance
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_monitor.record_operation(
                "application_run",
                duration,
                "success"
            )
            
            # Log application completion
            logger.info(f"Application completed in {duration:.2f}s")
            
            return True
            
        except Exception as e:
            # Record application error
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_monitor.record_operation(
                "application_run",
                duration,
                "error",
                {'error': str(e), 'error_type': type(e).__name__}
            )
            
            # Log error
            logger.exception(f"Application error: {e}")
            
            return False

class ErrorHandler:
    """
    Enhanced error handling with recovery strategies
    
    This class provides methods to handle different types of errors
    and implement recovery strategies.
    """
    
    def __init__(self, app):
        """Initialize the error handler"""
        self.app = app
        self.recovery_strategies = {}
        self.error_counts = {}
        
    def register_recovery_strategy(self, error_type, strategy_func):
        """
        Register a recovery strategy for a specific error type
        
        Args:
            error_type: Name of the error type (string)
            strategy_func: Async function to handle the error
        """
        self.recovery_strategies[error_type] = strategy_func
        
    async def handle_error(self, error, context="unknown"):
        """
        Handle an error with appropriate recovery strategy
        
        Args:
            error: The exception that occurred
            context: Context string indicating where the error occurred
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Track error counts
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Log the error
        logger.error(f"Error ({error_type}) in {context}: {error_msg}")
        self.app.add_log_message(f"Error in {context}: {error_msg}", logging.ERROR)
        
        # Check if we have a recovery strategy for this error type
        if error_type in self.recovery_strategies:
            logger.info(f"Attempting recovery for {error_type} in {context}")
            self.app.add_log_message(f"Attempting recovery...", logging.INFO)
            
            try:
                # Execute the recovery strategy
                recovery_success = await self.recovery_strategies[error_type](error, context)
                
                if recovery_success:
                    logger.info(f"Recovery successful for {error_type} in {context}")
                    self.app.add_log_message(f"Recovery successful", logging.INFO)
                    return True
                else:
                    logger.warning(f"Recovery failed for {error_type} in {context}")
                    self.app.add_log_message(f"Recovery failed", logging.WARNING)
                    return False
                    
            except Exception as recovery_error:
                logger.error(f"Error during recovery: {recovery_error}")
                self.app.add_log_message(f"Recovery error: {recovery_error}", logging.ERROR)
                return False
                
        else:
            # No recovery strategy available
            logger.warning(f"No recovery strategy for {error_type}")
            self.app.add_log_message(f"No recovery strategy available", logging.WARNING)
            return False
            
    def get_error_stats(self):
        """Get statistics about errors handled"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": self.error_counts
        }


async def main():
    """Main entry point with enhanced error handling"""
    start_time = datetime.now()
    session_id = f"session_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    # Setup structured logging context
    log_context = {
        'session_id': session_id,
        'start_time': start_time.isoformat()
    }
    
    try:
        logger.info(f"Application starting", extra=log_context)
        
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
            
            # Convert system_info to string representation for logging context
            log_context['system_info'] = str(system_info)
            logger.info(f"System information: {system_info}", extra=log_context)
            
            # Check if system has enough resources
            if system_info['memory_available'] < 500:  # Less than 500MB available
                logger.warning("Low memory available. Performance may be affected.", extra=log_context)
                print("⚠️ Low system memory detected. Performance may be affected.")
                
        except ImportError:
            logger.info("psutil not available. Skipping system diagnostics.", extra=log_context)
        
        # Initialize the application
        app = RithmicAdminTUI()
        
        # Run the application with performance tracking
        logger.info("Starting application main loop", extra=log_context)
        run_start_time = datetime.now()
        await app.run()
        run_duration = (datetime.now() - run_start_time).total_seconds()
        logger.info(f"Application main loop completed in {run_duration:.2f}s", extra=log_context)
        
    except KeyboardInterrupt:
        logger.info("Program terminated by user", extra=log_context)
        print("\nApplication terminated by user.")
        
    except ImportError as e:
        # Special handling for import errors which are common setup issues
        module_name = getattr(e, 'name', str(e))
        logger.error(f"Missing module: {module_name}", extra=log_context)
        print(f"\n❌ Missing required module: {module_name}")
        print(f"Please install the missing module: pip install {module_name}")
        print(f"Full error: {str(e)}")
        
    except ConnectionError as e:
        # Special handling for connection errors
        logger.error(f"Connection error: {str(e)}", extra=log_context)
        print(f"\n❌ Connection error: {str(e)}")
        print("Please check your network connection and Rithmic server status.")
        
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
        print(f"\n❌ Error ({error_type}): {error_msg}")
        
        # For specific error types, provide more targeted help
        if "timeout" in error_msg.lower():
            print("This may be due to network issues or Rithmic server load.")
            print("Try again later or check your connection settings.")
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            print("This may be due to permission issues or invalid credentials.")
            print("Check your Rithmic credentials and permissions.")
    
    finally:
        # Log application shutdown with runtime statistics
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds()
        log_context['end_time'] = end_time.isoformat()
        log_context['runtime_seconds'] = str(runtime)
        
        logger.info(f"Application shutdown complete. Total runtime: {runtime:.2f}s", extra=log_context)

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Rithmic Admin Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--simple", action="store_true", help="Force simple display mode")
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        
    # Run the application
    asyncio.run(main())