"""
Enhanced Rithmic Admin Tool - Main TUI Application Orchestrator

This is the main entry point for the modular Rithmic admin tool that provides
a rich terminal user interface for managing Rithmic data collection and database
operations for the futures trading system.

Components:
- Main RithmicAdminTUI class that orchestrates all operations
- Keyboard navigation and live display updates
- Integration with all admin modules
- Command-line interface support
- Graceful error handling and cleanup
"""

import asyncio
import argparse
import sys
import os
import signal
from typing import Optional, Dict, Any
from rich.console import Console
from rich.text import Text

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import keyboard handling - try different options
    try:
        import keyboard
        KEYBOARD_AVAILABLE = True
    except ImportError:
        try:
            import pynput.keyboard
            KEYBOARD_AVAILABLE = 'pynput'
        except ImportError:
            KEYBOARD_AVAILABLE = False
    
    # Import admin modules
    from .admin_core_classes import SystemStatus, TUIComponents, MENU_ITEMS, MENU_DESCRIPTIONS, DownloadProgress

    # Import specialized admin operation modules
    from .admin_rithmic_connection import RithmicConnectionManager
    from .admin_rithmic_symbols import RithmicSymbolManager
    from .admin_rithmic_historical import RithmicHistoricalManager
    from .admin_rithmic_operations import RithmicOperationsManager
    from .admin_database import DatabaseOperations
    from admin_display_manager import DisplayManager
    
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all admin modules are available in the current directory")
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
    
    def _progress_callback(self, message: str, progress: float = 0.0):
        """Internal progress callback for operation updates"""
        # Update status with progress information
        self.status.last_operation_result = message
        
        # If we have a live display, update it
        if hasattr(self, 'display_manager'):
            try:
                self.display_manager.update_live_display(self.selected_menu_index)
            except Exception:
                pass  # Ignore display update errors
        
    def setup_keyboard_handling(self):
        """Set up keyboard event handling based on available libraries."""
        if KEYBOARD_AVAILABLE == True:
            # Using keyboard library
            try:
                keyboard.on_press(self.on_key_press)
                self.keyboard_handler = 'keyboard'
            except Exception:
                self.keyboard_handler = None
        elif KEYBOARD_AVAILABLE == 'pynput':
            # Using pynput library
            try:
                import pynput.keyboard
                listener = pynput.keyboard.Listener(on_press=self.on_pynput_key_press)
                listener.start()
                self.keyboard_handler = 'pynput'
            except Exception:
                self.keyboard_handler = None
        else:
            self.keyboard_handler = None
    
    def on_key_press(self, event):
        """Handle keyboard events from keyboard library."""
        try:
            if hasattr(event, 'name'):
                key = event.name
            else:
                key = str(event)
            
            asyncio.create_task(self.process_key(key))
        except Exception:
            pass  # Ignore keyboard handling errors
    
    def on_pynput_key_press(self, key):
        """Handle keyboard events from pynput library."""
        try:
            if hasattr(key, 'char') and key.char:
                key_name = key.char
            elif hasattr(key, 'name'):
                key_name = key.name
            else:
                key_name = str(key)
            
            asyncio.create_task(self.process_key(key_name))
        except Exception:
            pass  # Ignore keyboard handling errors
    
    async def process_key(self, key: str):
        """Process keyboard input and update application state."""
        if not self.running or self.operation_in_progress:
            return
        
        key = key.lower()
        
        # Handle navigation keys
        if key in ['up', 'k']:
            self.selected_menu_index = (self.selected_menu_index - 1) % len(MENU_ITEMS)
        elif key in ['down', 'j']:
            self.selected_menu_index = (self.selected_menu_index + 1) % len(MENU_ITEMS)
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
                await self.handle_menu_selection(index)
        
        # Handle quit commands
        elif key in ['q', 'ctrl+c', 'escape']:
            await self.quit_application()
    
    def progress_callback(self, symbol: str, progress: DownloadProgress):
        """Callback function for operation progress updates."""
        self.status.download_progress[symbol] = progress
        
        # Update display with progress information
        self.tui_components.update_progress_info(symbol, progress)
    
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
                # Test both database and Rithmic connections
                db_result = await self.database_ops.test_connection()
                rithmic_result = await self.connection_manager.test_connection()
                
                result = {
                    "status": "success" if db_result and rithmic_result else "error",
                    "message": "Connection tests completed",
                    "details": {
                        "database": "Connected" if db_result else "Failed",
                        "rithmic": "Connected" if rithmic_result else "Failed"
                    }
                }
                
            elif operation_key == 'search_symbols':
                if hasattr(self.symbol_manager, 'search_and_check_symbols'):
                    result = await self.symbol_manager.search_and_check_symbols()
                else:
                    result = await self.symbol_manager.search_symbols()
                
            elif operation_key == 'download_data':
                if hasattr(self.historical_manager, 'download_historical_data'):
                    result = await self.historical_manager.download_historical_data()
                elif hasattr(self.historical_manager, 'download_data'):
                    result = await self.historical_manager.download_data()
                else:
                    result = {"status": "error", "message": "Download method not available"}
                
            elif operation_key == 'view_database':
                if hasattr(self.database_ops, 'view_database_data'):
                    result = await self.database_ops.view_database_data()
                else:
                    result = {"status": "error", "message": "View database method not available"}
                
            elif operation_key == 'initialize_db':
                result = await self.database_ops.initialize_database()
                
            elif operation_key == 'exit':
                await self.quit_application()
                return
            else:
                result = {"status": "error", "message": f"Unknown operation: {operation_key}"}
            
            # Store result for display
            self.last_operation_result = result
            if hasattr(self.tui_components, 'set_operation_result'):
                self.tui_components.set_operation_result(result)
            
            # Also update display manager if available
            if hasattr(self.display_manager, 'set_operation_result'):
                self.display_manager.set_operation_result(result)
            
        except Exception as e:
            error_result = {
                "status": "error", 
                "message": f"Operation failed: {str(e)}",
                "operation": self.current_operation
            }
            self.last_operation_result = error_result
            if hasattr(self.tui_components, 'set_operation_result'):
                self.tui_components.set_operation_result(error_result)
        
        finally:
            self.operation_in_progress = False
            self.current_operation = None
    
    async def quit_application(self):
        """Gracefully shut down the application."""
        self.running = False
        
        # Cleanup operations from all managers
        cleanup_tasks = []
        
        if hasattr(self.connection_manager, 'cleanup'):
            cleanup_tasks.append(self.connection_manager.cleanup())
        if hasattr(self.historical_manager, 'cleanup'):
            cleanup_tasks.append(self.historical_manager.cleanup())
        if hasattr(self.operations_manager, 'cleanup'):
            cleanup_tasks.append(self.operations_manager.cleanup())
        if hasattr(self.database_ops, 'cleanup'):
            cleanup_tasks.append(self.database_ops.cleanup())
            
        for task in cleanup_tasks:
            try:
                await task
            except Exception:
                pass  # Ignore individual cleanup errors
        
        # Stop keyboard handling
        if self.keyboard_handler == 'keyboard' and KEYBOARD_AVAILABLE == True:
            try:
                import keyboard
                keyboard.unhook_all()
            except Exception:
                pass
    
    async def run(self):
        """Main application event loop with live display updates."""
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            asyncio.create_task(self.quit_application())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initial display
        if hasattr(self.display_manager, 'show_welcome_message'):
            self.display_manager.show_welcome_message()
        
        # Main event loop
        while self.running:
            try:
                # Update display with current state
                if hasattr(self.display_manager, 'render_layout'):
                    self.display_manager.render_layout(
                        selected_menu_index=self.selected_menu_index,
                        current_operation=self.current_operation,
                        operation_in_progress=self.operation_in_progress
                    )
                
                # Handle fallback keyboard input if no handler available
                if not self.keyboard_handler and not self.operation_in_progress:
                    await self.handle_fallback_input()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                await self.quit_application()
                break
            except Exception as e:
                # Log error but continue running
                error_result = {
                    "status": "error",
                    "message": f"Application error: {str(e)}"
                }
                if hasattr(self.tui_components, 'set_operation_result'):
                    self.tui_components.set_operation_result(error_result)
                await asyncio.sleep(1)  # Brief pause before continuing
    
    async def handle_fallback_input(self):
        """Handle keyboard input when no async keyboard library is available."""
        # This is a fallback method - in a real implementation,
        # you might want to use threading or other methods for input
        pass
    
    def show_help(self):
        """Display help information about keyboard controls."""
        help_text = Text("\nKeyboard Controls:\n", style="bold cyan")
        help_text.append("↑/↓ or k/j: Navigate menu\n", style="white")
        help_text.append("Enter/Space: Execute selected item\n", style="white")
        help_text.append("1-5: Direct menu selection\n", style="white")
        help_text.append("0: Exit application\n", style="white")
        help_text.append("q/Ctrl+C: Quit\n", style="white")
        
        self.console.print(help_text)


class CommandLineInterface:
    """Command-line interface for batch operations."""
    
    def __init__(self):
        self.console = Console()
        self.status = SystemStatus()
        
        # Initialize specialized managers for CLI operations
        self.connection_manager = RithmicConnectionManager(self.cli_progress_callback)
        self.symbol_manager = RithmicSymbolManager(self.connection_manager, self.cli_progress_callback)
        self.historical_manager = RithmicHistoricalManager(self.connection_manager, self.cli_progress_callback)
        self.operations_manager = RithmicOperationsManager(self.cli_progress_callback)
        self.database_ops = DatabaseOperations(self.cli_progress_callback)
    
    def cli_progress_callback(self, symbol: str, progress: DownloadProgress):
        """Progress callback for CLI operations."""
        percentage = int(progress.progress * 100)
        self.console.print(f"[cyan]{symbol}[/cyan]: {percentage}% complete")
    
    async def run_command(self, command: str, **kwargs):
        """Execute a single command from the command line."""
        try:
            if command == 'test':
                # Test both connections
                db_result = await self.database_ops.test_connection()
                rithmic_result = await self.connection_manager.test_connection()
                result = {
                    "status": "success" if db_result and rithmic_result else "error",
                    "message": f"Database: {'✓' if db_result else '✗'}, Rithmic: {'✓' if rithmic_result else '✗'}"
                }
                
            elif command == 'search':
                result = await self.symbol_manager.search_symbols(**kwargs)
                
            elif command == 'download':
                result = await self.historical_manager.download_data(**kwargs)
                
            elif command == 'view':
                result = await self.database_ops.view_database_data()
                
            elif command == 'init':
                result = await self.database_ops.initialize_database()
                
            else:
                result = {"status": "error", "message": f"Unknown command: {command}"}
            
            # Display result
            if result.get("status") == "success":
                self.console.print(f"[green]✓[/green] {result.get('message', 'Operation completed')}")
            else:
                self.console.print(f"[red]✗[/red] {result.get('message', 'Operation failed')}")
            
            return result.get("status") == "success"
            
        except Exception as e:
            self.console.print(f"[red]Error:[/red] {str(e)}")
            return False
        finally:
            # Cleanup all managers
            try:
                await self.connection_manager.cleanup()
                await self.historical_manager.cleanup()
                await self.operations_manager.cleanup()
                await self.database_ops.cleanup()
            except Exception:
                pass


def create_cli_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Rithmic Futures Trading Admin Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enhanced_admin_rithmic.py                    # Interactive mode
  python enhanced_admin_rithmic.py test               # Test connections
  python enhanced_admin_rithmic.py search -s "NQ*"    # Search symbols
  python enhanced_admin_rithmic.py download -s NQM5   # Download data
  python enhanced_admin_rithmic.py init               # Initialize database
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['test', 'search', 'download', 'view', 'init'],
        help='Command to execute (omit for interactive mode)'
    )
    
    parser.add_argument(
        '-s', '--symbol',
        help='Symbol to work with (e.g., NQM5, ES*, etc.)'
    )
    
    parser.add_argument(
        '-e', '--exchange',
        default='CME',
        help='Exchange name (default: CME)'
    )
    
    parser.add_argument(
        '-d', '--days',
        type=int,
        default=7,
        help='Number of days for historical data (default: 7)'
    )
    
    parser.add_argument(
        '--help-keys',
        action='store_true',
        help='Show keyboard shortcuts for interactive mode'
    )
    
    return parser


async def main():
    """Main entry point for the application."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if args.help_keys:
        console = Console()
        console.print("\n[bold cyan]Rithmic Admin Tool - Keyboard Shortcuts[/bold cyan]\n")
        console.print("Interactive Mode Controls:")
        console.print("  ↑/↓ or k/j     Navigate menu items")
        console.print("  Enter/Space     Execute selected operation")
        console.print("  1-5             Direct menu selection")
        console.print("  0               Exit application")
        console.print("  q/Ctrl+C       Quit immediately")
        console.print("\nMenu Operations:")
        for i, item in enumerate(MENU_ITEMS, 1):
            key = str(i) if i < len(MENU_ITEMS) else "0"
            console.print(f"  {key}. {item['title']}")
        console.print()
        return
    
    # Command-line mode
    if args.command:
        cli = CommandLineInterface()
        kwargs = {}
        
        if args.symbol:
            kwargs['symbol'] = args.symbol
        if args.exchange:
            kwargs['exchange'] = args.exchange
        if args.days:
            kwargs['days'] = args.days
        
        success = await cli.run_command(args.command, **kwargs)
        sys.exit(0 if success else 1)
    
    # Interactive TUI mode
    else:
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
        print("\nApplication terminated by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
