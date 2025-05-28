"""
Quick Start Script for Rithmic Admin Tool
This script provides a fast-starting version that only connects to Rithmic when explicitly requested
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rithmic_admin")

# Try to import rich components
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Check if keyboard is available
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

class QuickStartAdmin:
    """Lightweight admin tool that only connects when requested"""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.running = True
        self.menu_items = [
            "Test Connections (DB + Rithmic)",
            "Search Symbols & Check Contracts", 
            "Download Historical Data",
            "View TimescaleDB Data",
            "Initialize/Setup Database",
            "Exit"
        ]
        self.current_menu_item = 0
        
    async def run(self):
        """Main run method"""
        print("Enhanced Rithmic Admin Tool Starting...")
        
        if RICH_AVAILABLE:
            await self.run_rich_display()
        else:
            await self.run_simple_display()
    
    async def run_rich_display(self):
        """Run a rich TUI display"""
        try:
            # Create a simple welcome layout
            layout = self.create_welcome_layout()
            
            with Live(layout, refresh_per_second=4, screen=True) as live:
                # Store the live display for later use
                self.live_display = live
                
                # Set up keyboard handling if available
                if KEYBOARD_AVAILABLE:
                    keyboard.on_press_key("up", lambda _: self.on_up())
                    keyboard.on_press_key("down", lambda _: self.on_down())
                    keyboard.on_press_key("enter", lambda _: self.on_enter())
                    keyboard.on_press_key("esc", lambda _: self.on_exit())
                
                # Main display loop
                while self.running:
                    try:
                        # Update the layout
                        layout = self.create_menu_layout()
                        live.update(layout)
                        
                        # Sleep to control refresh rate
                        await asyncio.sleep(0.25)
                        
                    except KeyboardInterrupt:
                        self.running = False
                        break
                    except Exception as e:
                        print(f"Display error: {e}")
                        await asyncio.sleep(1)
                
                # Clean up keyboard handlers
                if KEYBOARD_AVAILABLE:
                    keyboard.unhook_all()
        
        except Exception as e:
            print(f"Rich display error: {e}")
            await self.run_simple_display()
    
    def create_welcome_layout(self):
        """Create a simple welcome layout"""
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
    
    def create_menu_layout(self):
        """Create a menu layout"""
        layout = Layout()
        
        # Create the menu content
        menu_content = ""
        for i, item in enumerate(self.menu_items):
            if i == self.current_menu_item:
                menu_content += f"[bold green]> {item}[/bold green]\n"
            else:
                menu_content += f"  {item}\n"
        
        layout.update(
            Panel(
                Align.center(
                    Text.from_markup(
                        "[bold cyan]RITHMIC DATA ADMIN TOOL[/bold cyan]\n\n"
                        f"{menu_content}\n\n"
                        "Use arrow keys to navigate, Enter to select, Esc to exit"
                    ),
                    vertical="middle"
                ),
                title="Main Menu",
                border_style="cyan"
            )
        )
        
        return layout
    
    def on_up(self):
        """Handle up arrow key"""
        self.current_menu_item = max(0, self.current_menu_item - 1)
    
    def on_down(self):
        """Handle down arrow key"""
        self.current_menu_item = min(len(self.menu_items) - 1, self.current_menu_item + 1)
    
    def on_enter(self):
        """Handle enter key"""
        if self.current_menu_item == len(self.menu_items) - 1:  # Exit option
            self.running = False
        else:
            # Execute the selected menu item
            menu_name = self.menu_items[self.current_menu_item]
            print(f"Selected: {menu_name}")
            
            # Create a task to execute the menu item in the background
            # This keeps the UI responsive
            asyncio.create_task(self.execute_menu_item(self.current_menu_item))
    
    def on_exit(self):
        """Handle escape key"""
        self.running = False
    
    async def execute_menu_item(self, item_index):
        """Execute the selected menu item"""
        try:
            # Only import the necessary modules when they're needed
            from layer1_development.scripts.rithmic_admin.admin_operations import AdminOperations
            from layer1_development.scripts.rithmic_admin.admin_core_classes import SystemStatus
            
            # Create minimal objects needed for the operation
            status = SystemStatus()
            operations = AdminOperations(status, lambda x: self.show_result(x))
            
            # Execute the selected menu item
            if item_index == 0:  # Test Connections
                await operations.test_connections()
                
            elif item_index == 1:  # Search Symbols
                await operations.search_symbols_and_contracts()
                
            elif item_index == 2:  # Download Historical Data
                # Default to 7 days
                days = 7
                await operations.download_historical_data(days)
                
            elif item_index == 3:  # View TimescaleDB Data
                await operations.view_database_data()
                
            elif item_index == 4:  # Initialize Database
                await operations.initialize_database()
                
        except Exception as e:
            self.show_result(f"Error executing menu item: {e}")
    
    def show_result(self, result):
        """Show a result message"""
        if RICH_AVAILABLE and hasattr(self, 'live_display'):
            # Update the layout to show the result
            result_layout = self.create_result_layout(result)
            self.live_display.update(result_layout)
        else:
            # Just print the result
            print(f"\nResult: {result}")
            input("\nPress Enter to continue...")
    
    def create_result_layout(self, result):
        """Create a layout showing a result"""
        layout = Layout()
        
        layout.update(
            Panel(
                Align.center(
                    Text.from_markup(
                        "[bold cyan]RITHMIC DATA ADMIN TOOL[/bold cyan]\n\n"
                        "[yellow]Result:[/yellow]\n\n"
                        f"{result}\n\n"
                        "[dim]Press any key to return to the menu...[/dim]"
                    ),
                    vertical="middle"
                ),
                title="Operation Result",
                border_style="green"
            )
        )
        
        return layout
        
    async def execute_test_connections(self):
        """Execute the test connections menu item"""
        await self.execute_menu_item(0)
    
    async def run_simple_display(self):
        """Run a simple text-based display"""
        while self.running:
            try:
                # Clear the screen
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Display the menu
                print("\n" + "=" * 50)
                print(" Rithmic Admin Tool ".center(50, "="))
                print("=" * 50)
                print("\n")
                
                # Display menu items
                for i, item in enumerate(self.menu_items[:-1]):
                    prefix = ">" if i == self.current_menu_item else " "
                    print(f"{prefix} {i+1}. {item}")
                
                # Exit option
                prefix = ">" if len(self.menu_items) - 1 == self.current_menu_item else " "
                print(f"{prefix} 0. {self.menu_items[-1]}")
                print("-" * 50)
                
                # Get user input
                choice = input("\nEnter choice (or use arrow keys): ").strip()
                
                if choice.isdigit():
                    choice_num = int(choice)
                    if choice_num == 0:
                        self.running = False
                    elif 1 <= choice_num <= len(self.menu_items) - 1:
                        # Execute the menu item (convert to 0-based index)
                        await self.execute_menu_item(choice_num - 1)
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"Display error: {e}")
                await asyncio.sleep(1)

async def main():
    """Main entry point"""
    try:
        app = QuickStartAdmin()
        await app.run()
    except Exception as e:
        print(f"Application error: {e}")

if __name__ == "__main__":
    # Set up asyncio policy for Windows
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except AttributeError:
            pass  # Older Python versions
    
    # Run the application
    asyncio.run(main())