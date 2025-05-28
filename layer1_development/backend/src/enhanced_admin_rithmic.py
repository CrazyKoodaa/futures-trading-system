"""
Enhanced Rithmic Admin Tool - Fixed Import Version

This is the main entry point for the modular Rithmic admin tool that provides
a rich terminal user interface for managing Rithmic data collection and database
operations for the futures trading system.

Fixed to resolve relative import issues when running directly.
"""

import asyncio
import argparse
import sys
import os
import signal
from typing import Optional, Dict, Any
from rich.console import Console
from rich.text import Text

# Add the current directory to Python path to resolve imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add parent directories to path for config imports
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import built-in keyboard handling (cross-platform)
try:
    import msvcrt  # Windows
    KEYBOARD_AVAILABLE = 'msvcrt'
except ImportError:
    try:
        import termios
        import tty
        import select  # Import select at module level for Unix systems
        KEYBOARD_AVAILABLE = 'termios'
    except ImportError:
        KEYBOARD_AVAILABLE = False

# Import admin modules with absolute imports (fixed)
try:
    from admin_core_classes import SystemStatus, TUIComponents, MENU_ITEMS, MENU_DESCRIPTIONS, DownloadProgress

    # Import specialized admin operation modules
    from admin_rithmic_connection import RithmicConnectionManager
    from admin_rithmic_symbols import RithmicSymbolManager
    from admin_rithmic_historical import RithmicHistoricalManager
    from admin_rithmic_operations import RithmicOperationsManager
    from admin_database import DatabaseOperations
    from admin_display_manager import DisplayManager
    
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all admin modules are available in the current directory")
    print("\nTroubleshooting steps:")
    print("1. Make sure you're in the correct directory")
    print("2. Check that all .py files exist in the directory")
    print("3. Install required packages: pip install -r requirements.txt")
    print("4. Ensure async_rithmic is installed and accessible")
    sys.exit(1)


class RithmicAdminTUI:
    """
    Main TUI application class that orchestrates all admin operations
    with live keyboard navigation and rich display updates.
    """
    
    def __init__(self):
        """Initialize the TUI application with all required components."""
        self.console = Console()
        self.status = SystemStatus()
        self.tui_components = TUIComponents(self.status)
        self.display_manager = DisplayManager(self.console, self.tui_components, self.status)
        
        # Initialize specialized operation managers with proper callback
        self.connection_manager = RithmicConnectionManager(self._progress_callback)
        self.symbol_manager = RithmicSymbolManager(self.connection_manager, self._progress_callback)
        self.historical_manager = RithmicHistoricalManager(self.connection_manager, self._progress_callback)
        self.operations_manager = RithmicOperationsManager(self._progress_callback)
        self.database_ops = DatabaseOperations(self._progress_callback)
        
        # Navigation state
        self.selected_menu_index = 0
        self.running = True
        self.last_operation_result = None
        
        # Keyboard handling
        self.keyboard_handler = None
        self.setup_keyboard_handling()
        
        # Operation tracking
        self.current_operation = None
        self.operation_in_progress = False
    
    def _progress_callback(self, *args, **kwargs):
        """Internal progress callback for operation updates - flexible signature"""
        # Handle different callback signatures
        message = "Progress update"
        progress = 0.0
        
        if len(args) >= 1:
            message = str(args[0])
        if len(args) >= 2 and isinstance(args[1], (int, float)):
            progress = float(args[1])
        
        # Handle keyword arguments
        if 'message' in kwargs:
            message = str(kwargs['message'])
        if 'progress' in kwargs:
            progress = float(kwargs['progress'])
        
        # Update status with progress information
        self.status.last_operation_result = message
        
        # If we have a live display, update it
        if hasattr(self, 'display_manager'):
            try:
                self.display_manager.update_live_display(self.selected_menu_index)
            except Exception:
                pass  # Ignore display update errors
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update status in the TUI instead of using print statements"""
        try:
            self.status.last_operation_result = f"[{status_type.upper()}] {message}"
            if hasattr(self, 'display_manager') and self.display_manager:
                self.display_manager.update_live_display(self.selected_menu_index)
        except Exception:
            pass  # Fail silently if display update fails
    
    def _build_connection_test_results(self, db_success: bool, db_message: str, 
                                     rithmic_success: bool, rithmic_message: str, 
                                     overall_success: bool) -> str:
        """Build detailed connection test results in markdown format."""
        from datetime import datetime
        
        # Header
        status_icon = "✅" if overall_success else "❌"
        overall_status = "SUCCESS" if overall_success else "FAILED"
        
        markdown = f"# {status_icon} Connection Test Results - {overall_status}\n\n"
        markdown += f"**Test completed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Database Connection Results
        db_icon = "✅" if db_success else "❌"
        db_status = "SUCCESS" if db_success else "FAILED"
        
        markdown += f"## {db_icon} Database Connection - {db_status}\n\n"
        markdown += f"**Status:** {'Connected' if db_success else 'Failed'}\n\n"
        
        if db_message:
            # Clean up the message and format it properly
            clean_db_msg = db_message.replace('❌', '').replace('✅', '').strip()
            if db_success:
                markdown += f"**Details:** {clean_db_msg}\n\n"
            else:
                markdown += f"**Error:** {clean_db_msg}\n\n"
        
        markdown += "**Service:** TimescaleDB PostgreSQL\n\n"
        markdown += "**Module:** admin_database.py\n\n"
        
        # Rithmic Connection Results
        rithmic_icon = "✅" if rithmic_success else "❌"
        rithmic_status = "SUCCESS" if rithmic_success else "FAILED"
        
        markdown += f"## {rithmic_icon} Rithmic API Connection - {rithmic_status}\n\n"
        markdown += f"**Status:** {'Connected' if rithmic_success else 'Failed'}\n\n"
        
        if rithmic_message:
            # Clean up the message and format it properly
            clean_rithmic_msg = rithmic_message.replace('❌', '').replace('✅', '').strip()
            if rithmic_success:
                markdown += f"**Details:** {clean_rithmic_msg}\n\n"
            else:
                markdown += f"**Error:** {clean_rithmic_msg}\n\n"
        
        markdown += "**Gateway:** Chicago Gateway\n\n"
        markdown += "**Module:** admin_rithmic_connection.py\n\n"
        
        # Summary
        markdown += "## 📊 Test Summary\n\n"
        
        if overall_success:
            markdown += "**Result:** All connections are working properly! 🎉\n\n"
            markdown += "**Next Steps:**\n"
            markdown += "- You can now search for symbols\n"
            markdown += "- Download historical data\n"
            markdown += "- View database contents\n\n"
        else:
            markdown += "**Result:** One or more connections failed! ⚠️\n\n"
            markdown += "**Troubleshooting:**\n"
            if not db_success:
                markdown += "- Check database server is running\n"
                markdown += "- Verify connection credentials\n"
                markdown += "- Ensure TimescaleDB extension is installed\n"
            if not rithmic_success:
                markdown += "- Verify Rithmic API credentials\n"
                markdown += "- Check network connectivity\n"
                markdown += "- Ensure Chicago gateway is accessible\n"
            markdown += "\n"
        
        # Connection Status Table
        markdown += "## 🔗 Connection Status Overview\n\n"
        markdown += "| Service | Status | Module |\n"
        markdown += "|---------|--------|--------|\n"
        markdown += f"| Database | {'🟢 Connected' if db_success else '🔴 Failed'} | admin_database.py |\n"
        markdown += f"| Rithmic API | {'🟢 Connected' if rithmic_success else '🔴 Failed'} | admin_rithmic_connection.py |\n\n"
        
        return markdown
        
    def setup_keyboard_handling(self):
        """Set up keyboard event handling based on available libraries."""
        self.keyboard_handler = KEYBOARD_AVAILABLE
        # No external library setup needed - we'll handle input in the main loop
    
    def get_key_input(self):
        """Get keyboard input using built-in methods - non-blocking."""
        if self.keyboard_handler == 'msvcrt':
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\xe0':  # Arrow keys prefix on Windows
                    key = msvcrt.getch()
                    if key == b'H': return 'up'
                    elif key == b'P': return 'down'
                    elif key == b'K': return 'left'
                    elif key == b'M': return 'right'
                elif key == b'\r':  # Enter key
                    return 'enter'
                elif key == b'\x1b':  # Escape key
                    return 'escape'
                return key.decode('utf-8', errors='ignore')
        elif self.keyboard_handler == 'termios':
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                if key == '\x1b':  # ESC sequence
                    if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                        key += sys.stdin.read(2)
                        if key == '\x1b[A': return 'up'
                        elif key == '\x1b[B': return 'down'
                        elif key == '\x1b[C': return 'right'
                        elif key == '\x1b[D': return 'left'
                    return 'escape'
                elif key == '\r' or key == '\n':  # Enter key
                    return 'enter'
                return key
        return None
    
    async def process_key(self, key: str):
        """Process keyboard input and update application state."""
        if not self.running or self.operation_in_progress:
            return
        
        key = key.lower()
        display_needs_update = False
        
        # Handle navigation keys
        if key in ['up', 'k']:
            self.selected_menu_index = (self.selected_menu_index - 1) % len(MENU_ITEMS)
            display_needs_update = True
        elif key in ['down', 'j']:
            self.selected_menu_index = (self.selected_menu_index + 1) % len(MENU_ITEMS)
            display_needs_update = True
        elif key in ['enter', 'return', 'space']:
            await self.handle_menu_selection(self.selected_menu_index)
        
        # Handle direct menu selection
        elif key.isdigit():
            index = int(key)
            if index == 0:
                index = len(MENU_ITEMS) - 1  # Exit option
            else:
                index -= 1  # Convert to 0-based index
            
            if 0 <= index < len(MENU_ITEMS):
                self.selected_menu_index = index
                display_needs_update = True
                await self.handle_menu_selection(index)
        
        # Handle quit commands
        elif key in ['q', 'ctrl+c', 'escape']:
            await self.quit_application()
        
        # Update display if navigation changed
        if display_needs_update:
            self.display_manager.update_live_display(self.selected_menu_index)
    
    async def handle_menu_selection(self, index: int):
        """Execute the operation corresponding to the selected menu index."""
        if self.operation_in_progress:
            return

        self.operation_in_progress = True
        self.current_operation = MENU_ITEMS[index]['title']
        
        try:
            operation_key = MENU_ITEMS[index]['key']
            
            # Map menu operations to specialized manager methods
            if operation_key == 'test_connections':
                # Test both database and Rithmic connections with detailed results
                self._update_status("🔄 Testing connections...", "info")
                
                # Test database connection
                self._update_status("Testing database connection...", "info")
                db_success, db_message = await self.database_ops.test_connection()
                
                # Test Rithmic connection  
                self._update_status("Testing Rithmic connection...", "info")
                rithmic_success, rithmic_message = await self.connection_manager.test_connection()
                
                # Update system status flags
                self.status.database_connected = db_success
                self.status.rithmic_connected = rithmic_success
                
                # Create comprehensive result with markdown formatting
                overall_success = db_success and rithmic_success
                
                # Build detailed markdown result
                result_markdown = self._build_connection_test_results(
                    db_success, db_message, rithmic_success, rithmic_message, overall_success
                )
                
                result = {
                    "status": "success" if overall_success else "error",
                    "message": result_markdown,
                    "details": {
                        "database": {"success": db_success, "message": db_message},
                        "rithmic": {"success": rithmic_success, "message": rithmic_message}
                    }
                }
                
            elif operation_key == 'search_symbols':
                # Use a method that actually exists or provide fallback
                if hasattr(self.symbol_manager, 'search_symbols'):
                    result = await self.symbol_manager.search_symbols("NQ*", "CME")
                else:
                    result = {"status": "error", "message": "Symbol search method not available"}
                
            elif operation_key == 'download_data':
                if hasattr(self.historical_manager, 'download_historical_data'):
                    result = await self.historical_manager.download_historical_data(["NQZ24"], days=7)
                else:
                    result = {"status": "error", "message": "Download method not available"}
                
            elif operation_key == 'view_database':
                if hasattr(self.database_ops, 'get_database_summary'):
                    result = await self.database_ops.get_database_summary()
                else:
                    result = {"status": "error", "message": "View database method not available"}
                
            elif operation_key == 'initialize_db':
                success, message = await self.database_ops.initialize_database()
                result = {"status": "success" if success else "error", "message": message}
                
            elif operation_key == 'exit':
                await self.quit_application()
                return
            else:
                result = {"status": "error", "message": f"Unknown operation: {operation_key}"}
            
            # Store result for display - ensure it's always a proper dict
            if isinstance(result, dict):
                self.last_operation_result = result
                # Store the message in the status for display
                if "message" in result:
                    self.status.last_operation_result = result["message"]
                else:
                    self.status.last_operation_result = "Operation completed"
            else:
                # Convert non-dict results to proper format
                self.last_operation_result = {
                    "status": "info",
                    "message": str(result) if result else "Operation completed"
                }
                self.status.last_operation_result = str(result) if result else "Operation completed"
            
            # Update TUI components if available
            if hasattr(self.tui_components, 'set_operation_result'):
                self.tui_components.set_operation_result(self.last_operation_result)
            
            # Also update display manager if available
            if hasattr(self.display_manager, 'set_operation_result'):
                self.display_manager.set_operation_result(self.last_operation_result)
            
        except Exception as e:
            error_message = f"❌ **Operation Failed: {self.current_operation}**\n\n**Error:** {str(e)}\n\n**Troubleshooting:**\n- Check connection settings\n- Verify credentials\n- Ensure services are running"
            
            error_result = {
                "status": "error", 
                "message": error_message,
                "operation": self.current_operation
            }
            self.last_operation_result = error_result
            self.status.last_operation_result = error_message
            
            # Update TUI components with error
            if hasattr(self.tui_components, 'set_operation_result'):
                self.tui_components.set_operation_result(error_result)
        
        finally:
            self.operation_in_progress = False
            self.current_operation = None
    
    async def quit_application(self):
        """Gracefully shut down the application."""
        self.running = False
        self._update_status("Shutting down application...", "info")
        
        # Cleanup operations from all managers
        cleanup_managers = [
            ("connection_manager", self.connection_manager),
            ("historical_manager", self.historical_manager), 
            ("operations_manager", self.operations_manager),
            ("database_ops", self.database_ops)
        ]
        
        for manager_name, manager in cleanup_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    self._update_status(f"Cleaning up {manager_name}...", "info")
                    await manager.cleanup()
                except Exception as e:
                    self._update_status(f"Error during {manager_name} cleanup: {str(e)}", "error")
        
        # Stop keyboard handling
        if self.keyboard_handler == 'keyboard' and KEYBOARD_AVAILABLE == True:
            try:
                import keyboard
                keyboard.unhook_all()
                self._update_status("Keyboard handler stopped", "info")
            except Exception as e:
                self._update_status(f"Error stopping keyboard handler: {str(e)}", "error")
    
    async def run(self):
        """Main application event loop with live display updates."""
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            asyncio.create_task(self.quit_application())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start live display mode for smooth updates
        self.display_manager.start_live_display()
        
        try:
            # Initial layout update with welcome message
            self._update_status("Welcome to Rithmic Admin Tool! Use ↑/↓ or j/k to navigate, Enter to select.", "info")
            
            # Main event loop - no more constant printing!
            while self.running:
                try:
                    # Handle keyboard input if handler is available
                    if self.keyboard_handler and not self.operation_in_progress:
                        key = self.get_key_input()
                        if key:
                            await self.process_key(key)
                    elif not self.keyboard_handler and not self.operation_in_progress:
                        await self.handle_fallback_input()
                    
                    # Shorter delay for more responsive input
                    await asyncio.sleep(0.1)
                    
                except KeyboardInterrupt:
                    await self.quit_application()
                    break
                except Exception as e:
                    # Log error but continue running - update status instead of print
                    self._update_status(f"Application error: {str(e)}", "error")
                    await asyncio.sleep(1)  # Brief pause before continuing
        
        finally:
            # Stop live display when exiting
            self.display_manager.stop_live_display()
    
    async def handle_fallback_input(self):
        """Handle keyboard input when no async keyboard library is available."""
        # Display a simple menu prompt and wait for input
        self._update_status("No keyboard handler available. Use 'q' to quit or run with proper terminal.", "warning")
        
        # Check for standard input in a simple way
        try:
            # This is a basic fallback - for full functionality, proper keyboard handling is needed
            import select
            if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                key = sys.stdin.read(1).strip().lower()
                if key:
                    await self.process_key(key)
        except (ImportError, OSError):
            # If even select is not available, just wait
            await asyncio.sleep(1.0)


async def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Rithmic Futures Trading Admin Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enhanced_admin_rithmic_fixed.py              # Interactive mode
        """
    )
    
    # Interactive TUI mode
    app = RithmicAdminTUI()
    try:
        await app.run()
    except KeyboardInterrupt:
        pass  # Graceful exit
    finally:
        # Ensure cleanup
        try:
            await app.quit_application()
        except Exception:
            pass


if __name__ == "__main__":
    """Entry point with proper error handling."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Final cleanup - can't avoid this print as TUI is shutdown
        print("\nApplication terminated by user")
    except Exception as e:
        # Fatal startup error - TUI not available yet
        print(f"Fatal error during startup: {e}")
        sys.exit(1)
