"""
Display Manager for Enhanced Rithmic Admin Tool
Handles all display modes and rendering logic
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich.layout import Layout
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger("rithmic_admin.display")

class DisplayManager:
    """Manages different display modes and rendering"""
    
    def __init__(self, status, tui_components):
        self.status = status
        self.tui_components = tui_components
        self.console = Console() if RICH_AVAILABLE else None
        self.live_display = None
        self.layout = None  # Will hold the main layout structure
        self.display_mode = "auto"  # auto, rich, simple
        self.refresh_rate = 10  # Hz
        self.last_update = 0
        self.update_counter = 0
        
        # Display state
        self.current_menu_item = 0
        self.results_content = ""
        self.show_results = False
        self.show_help = False
        self.running = True
        self.menu_items = []  # Will be populated when run_rich_display is called
        
        # Performance tracking
        self.frame_times = []
        self.max_frame_history = 100
        
        # Auto-detect best display mode
        self._detect_display_mode()
    
    def _detect_display_mode(self):
        """Auto-detect the best available display mode"""
        try:
            if RICH_AVAILABLE:
                # Test Rich console capabilities
                if self.console and self.console.is_terminal:
                    self.display_mode = "rich"
                    logger.info("Using Rich TUI display mode")
                else:
                    self.display_mode = "simple"
                    logger.info("Rich available but no terminal - using simple mode")
            else:
                self.display_mode = "simple"
                logger.info("Rich not available - using simple display mode")
        except Exception as e:
            logger.warning(f"Display mode detection failed: {e}")
            self.display_mode = "simple"
    
    def set_display_mode(self, mode: str):
        """Manually set display mode"""
        if mode in ["auto", "rich", "simple"]:
            self.display_mode = mode
            if mode == "auto":
                self._detect_display_mode()
    
    def update_menu_selection(self, menu_item: int):
        """Update current menu selection"""
        self.current_menu_item = menu_item
        # If we have a live display, update just the menu panel
        if self.live_display and self.layout and hasattr(self, 'menu_items'):
            menu_panel = self.tui_components.create_menu_panel(self.current_menu_item, self.menu_items)
            if menu_panel:
                self.layout["body"]["menu"].update(menu_panel)
    
    def update_results(self, content: str, show: bool = True):
        """Update results content"""
        self.results_content = content
        self.show_results = show
        # If we have a live display, update just the results panel
        if self.live_display and self.layout:
            results_panel = self.tui_components.create_results_panel(self.results_content, self.show_results)
            if results_panel:
                self.layout["results_container"].update(results_panel)
    
    def clear_results(self):
        """Clear results display"""
        self.results_content = ""
        self.show_results = False
        # If we have a live display, update just the results panel
        if self.live_display and self.layout:
            self.layout["results_container"].update(
                Panel("", title="📊 Results", border_style="dim")
            )
    
    def show_help_panel(self, show: bool = True):
        """Toggle help panel display"""
        self.show_help = show
        
    def show_popup_dialog(self, title: str, prompt: str, options: Optional[List[str]] = None) -> str:
        """
        Display a popup dialog for user input
        
        Args:
            title: Dialog title
            prompt: Prompt message
            options: Optional list of options to select from
            
        Returns:
            User input or selected option
        """
        try:
            # Store current terminal state
            self.status.add_log_message(f"Showing popup dialog: {title}")
            
            # Clear terminal
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Print dialog header
            print("\n" + "=" * 60)
            print(f" {title} ".center(60, "="))
            print("=" * 60 + "\n")
            
            # Print prompt
            print(f"{prompt}\n")
            
            # If options are provided, display them as a menu
            if options and isinstance(options, list) and len(options) > 0:
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option}")
                print("\nEnter the number of your selection (or 'q' to cancel):")
                
                # Get user input with timeout
                user_input = input("> ").strip()
                if user_input.lower() == 'q':
                    return ""  # Return empty string instead of None
                
                try:
                    selection = int(user_input)
                    if 1 <= selection <= len(options):
                        result = options[selection-1]
                    else:
                        print(f"Invalid selection. Using first option.")
                        result = options[0] if options else ""
                except ValueError:
                    print(f"Invalid input. Using first option.")
                    result = options[0] if options else ""
            else:
                # Simple text input
                print("Enter your input (or 'q' to cancel):")
                user_input = input("> ").strip()
                result = "" if user_input.lower() == 'q' else user_input
            
            # Clear terminal again
            os.system('cls' if os.name == 'nt' else 'clear')
            
            return result
            
        except Exception as e:
            # Log the error and return a default value
            self.status.add_log_message(f"Error in popup dialog: {str(e)}")
            print(f"Error in dialog: {str(e)}")
            return ""  # Return empty string instead of None
    
    async def run_rich_display(self, menu_items: List[str]):
        """Run Rich TUI display with live updates using optimized rendering"""
        if not RICH_AVAILABLE or self.display_mode != "rich":
            return False
        
        try:
            # Create the initial layout structure once
            self.layout = self._create_layout_structure()
            
            # Initialize the Live display with the layout structure
            with Live(
                self.layout,
                refresh_per_second=self.refresh_rate,
                screen=True,
                console=self.console,
                transient=False  # Ensure content stays on screen
            ) as live:
                
                self.live_display = live
                
                # Initial update of all panels
                self._update_all_panels(menu_items)
                
                while self.running:
                    try:
                        start_time = time.time()
                        
                        # Update only the panels that need updating
                        # This is more efficient than recreating the entire layout
                        self._update_dynamic_panels(menu_items)
                        
                        # Track performance
                        frame_time = time.time() - start_time
                        self._track_performance(frame_time)
                        
                        # Control refresh rate
                        sleep_time = max(0, (1.0 / self.refresh_rate) - frame_time)
                        await asyncio.sleep(sleep_time)
                        
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        logger.error(f"Rich display error: {e}")
                        await asyncio.sleep(1)
                
                self.live_display = None
                return True
                
        except Exception as e:
            logger.error(f"Rich display failed: {e}")
            return False
            
    def _create_layout_structure(self):
        """Create the main layout structure without content
        This creates the panel structure once, then we'll update panel contents separately"""
        if not RICH_AVAILABLE:
            return None
            
        # Create layout
        layout = Layout()
        
        # Create the basic structure
        layout.split_column(
            Layout(name="header", size=6),
            Layout(name="body", ratio=2),
            Layout(name="results_container", ratio=1),
            Layout(name="log", size=12),
            Layout(name="footer", size=3)
        )
        
        # Split the body section
        body_layout = Layout()
        body_layout.split_row(
            Layout(name="status_progress", ratio=1),
            Layout(name="menu", ratio=1)
        )
        
        # Split the status_progress section
        status_progress_layout = Layout()
        status_progress_layout.split_column(
            Layout(name="status", size=8),
            Layout(name="progress", size=12)
        )
        
        # Update the nested layouts
        layout["body"].update(body_layout)
        layout["body"]["status_progress"].update(status_progress_layout)
        
        # Initialize with empty panels
        layout["header"].update(Panel("", border_style="cyan"))
        layout["body"]["status_progress"]["status"].update(Panel("", title="System Status", border_style="blue"))
        layout["body"]["status_progress"]["progress"].update(Panel("", title="📊 Download Progress", border_style="green"))
        layout["body"]["menu"].update(Panel("", title="Navigation", border_style="yellow"))
        layout["results_container"].update(Panel("", title="📊 Results", border_style="green"))
        layout["log"].update(Panel("", title="📝 System Log", border_style="blue"))
        layout["footer"].update(Panel("", border_style="dim"))
        
        return layout
        
    def _update_all_panels(self, menu_items: List[str]):
        """Update all panels in the layout"""
        if not RICH_AVAILABLE or not self.layout:
            return
            
        # Update header
        self.layout["header"].update(
            Panel(
                Align.center(
                    Text("RITHMIC DATA ADMIN TOOL", style="bold cyan"),
                    vertical="middle"
                ),
                border_style="cyan"
            )
        )
        
        # Update status panel
        status_panel = self.tui_components.create_status_panel()
        if status_panel:
            self.layout["body"]["status_progress"]["status"].update(status_panel)
        
        # Update progress panel
        progress_panel = self.tui_components.create_progress_panel()
        if progress_panel:
            self.layout["body"]["status_progress"]["progress"].update(progress_panel)
        
        # Update menu panel
        menu_panel = self.tui_components.create_menu_panel(self.current_menu_item, menu_items)
        if menu_panel:
            self.layout["body"]["menu"].update(menu_panel)
        
        # Update results panel
        results_panel = self.tui_components.create_results_panel(self.results_content, self.show_results)
        if results_panel:
            self.layout["results_container"].update(results_panel)
        
        # Update log panel
        log_panel = self.tui_components.create_log_panel()
        if log_panel:
            self.layout["log"].update(log_panel)
        
        # Update footer
        self.layout["footer"].update(
            Panel(
                Align.center("🎯 Enhanced Rithmic Admin Tool • Press Ctrl+C to exit"),
                border_style="dim"
            )
        )
    
    def _update_dynamic_panels(self, menu_items: List[str]):
        """Update only the panels that change frequently"""
        if not RICH_AVAILABLE or not self.layout:
            return
        
        # Update progress panel (changes frequently during downloads)
        progress_panel = self.tui_components.create_progress_panel()
        if progress_panel:
            self.layout["body"]["status_progress"]["progress"].update(progress_panel)
        
        # Update menu panel (changes with selection)
        menu_panel = self.tui_components.create_menu_panel(self.current_menu_item, menu_items)
        if menu_panel:
            self.layout["body"]["menu"].update(menu_panel)
        
        # Update results panel if showing
        if self.show_results:
            results_panel = self.tui_components.create_results_panel(self.results_content, self.show_results)
            if results_panel:
                self.layout["results_container"].update(results_panel)
        
        # Update log panel (changes with new messages)
        log_panel = self.tui_components.create_log_panel()
        if log_panel:
            self.layout["log"].update(log_panel)
    
    def _create_rich_layout(self, menu_items: List[str]):
        """Create Rich layout based on current state (legacy method)"""
        if not RICH_AVAILABLE:
            return None
            
        # Store menu_items for use in other methods
        self.menu_items = menu_items
            
        if self.show_help:
            return self._create_help_layout()
        elif self.layout:
            # If we already have a layout, update all panels and return it
            self._update_all_panels(menu_items)
            return self.layout
        else:
            # Create a new layout structure and update all panels
            self.layout = self._create_layout_structure()
            self._update_all_panels(menu_items)
            return self.layout
    
    def _create_help_layout(self):
        """Create help display layout"""
        if not RICH_AVAILABLE:
            return None
        
        help_content = """
[bold cyan]🎯 Keyboard Shortcuts[/bold cyan]

[bold yellow]Navigation:[/bold yellow]
• [bold]↑/↓ Arrow Keys[/bold]: Navigate menu items
• [bold]Enter[/bold]: Execute selected menu item
• [bold]1-5[/bold]: Direct menu selection
• [bold]0[/bold]: Exit application

[bold yellow]Control:[/bold yellow]
• [bold]Esc[/bold]: Exit application
• [bold]Ctrl+C[/bold]: Force exit
• [bold]q[/bold]: Quit application
• [bold]h[/bold] or [bold]?[/bold]: Show this help
• [bold]c[/bold]: Clear results
• [bold]r[/bold]: Refresh display
"""
        
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.layout import Layout
        
        layout = Layout()
        layout.split_column(
            Layout(
                Panel(
                    Markdown(help_content),
                    title="Help & Keyboard Shortcuts",
                    border_style="cyan"
                ),
                ratio=1
            )
        )
        
        return layout
    
    def _create_simple_display(self, menu_items: List[str]):
        """Create simple text-based display"""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Header
        print("=" * 80)
        print("RITHMIC DATA ADMIN TOOL")
        print("=" * 80)
        
        # Status section
        self._print_status_section()
        
        # Progress section (if active)
        if self.status.download_progress:
            self._print_progress_section()
        
        # Menu section
        self._print_menu_section(menu_items)
        
        # Results section (if visible)
        if self.show_results and self.results_content:
            self._print_results_section()
        
        # Help section (if visible)
        if self.show_help:
            self._print_help_section()
        
        # Footer
        print("=" * 80)
    
    def _print_status_section(self):
        """Print status information in simple mode"""
        print("\nSystem Status:")
        print("-" * 40)
        
        # Connection status
        rithmic_status = "[CONNECTED]" if self.status.rithmic_connected else "[DISCONNECTED]"
        db_status = "[CONNECTED]" if self.status.db_connected else "[DISCONNECTED]"
        
        print(f"Rithmic:  {rithmic_status}")
        print(f"Database: {db_status}")
        print(f"Exchange: {self.status.current_exchange}")
        
        # Symbols and contracts
        if self.status.current_symbols:
            print(f"Symbols:  {', '.join(self.status.current_symbols)}")
        else:
            print("Symbols:  None selected")
        
        if self.status.available_contracts:
            contracts_info = []
            for symbol, contracts in self.status.available_contracts.items():
                contracts_info.append(f"{symbol}:{contracts[0] if contracts else 'N/A'}")
            print(f"Contracts: {' | '.join(contracts_info)}")
    
    def _print_progress_section(self):
        """Print download progress in simple mode"""
        print("\nDownload Progress:")
        print("-" * 40)
        
        for key, progress in self.status.download_progress.items():
            progress_percent = progress.progress_percent
            
            # Create simple progress bar
            bar_length = 30
            filled_length = int(bar_length * progress_percent / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            print(f"{progress.contract} ({progress.data_type}):")
            print(f"  [{bar}] {progress_percent:.1f}%")
            print(f"  Chunks: {progress.completed_chunks}/{progress.total_chunks}")
            print(f"  Records: {progress.total_records:,}")
            
            # Show status
            if progress.completed_chunks >= progress.total_chunks:
                status = "[COMPLETE]"
            elif "Error" in progress.current_chunk_info:
                status = "[ERROR]"
            elif "Saving" in progress.current_chunk_info:
                status = "[SAVING]"
            else:
                status = "[DOWNLOADING]"
            
            print(f"  Status: {status}")
            print()
    
    def _print_menu_section(self, menu_items: List[str]):
        """Print menu in simple mode"""
        print("\nMain Menu:")
        print("-" * 40)
        
        for i, item in enumerate(menu_items):
            marker = "→" if i == self.current_menu_item else " "
            number = i + 1 if i < len(menu_items) - 1 else 0  # Last item is 0 (Exit)
            print(f"{marker} {number}. {item}")
        
        print("\nNavigation: Use numbers (1-5, 0) or arrow keys + Enter")
        print("Other keys: h=help, c=clear, q=quit")
    
    def _print_results_section(self):
        """Print results in simple mode"""
        print("\nResults:")
        print("-" * 40)
        
        # Convert markdown-style content to plain text
        content = self.results_content
        content = content.replace("**", "")  # Remove bold markdown
        content = content.replace("##", "")  # Remove headers
        content = content.replace("###", "")
        content = content.replace("✅", "[OK]")
        content = content.replace("❌", "[ERROR]")
        content = content.replace("⚠️", "[WARNING]")
        content = content.replace("📊", "[INFO]")
        content = content.replace("🔍", "[SEARCH]")
        content = content.replace("📥", "[DOWNLOAD]")
        content = content.replace("🔧", "[SETUP]")
        
        # Print with word wrapping
        lines = content.split('\n')
        for line in lines[:20]:  # Limit to 20 lines
            if line.strip():
                print(line.strip())
        
        if len(lines) > 20:
            print(f"... ({len(lines) - 20} more lines)")
    
    def _print_help_section(self):
        """Print help in simple mode"""
        print("\nKeyboard Shortcuts:")
        print("-" * 40)
        print("Navigation:")
        print("  ↑/↓ Arrow Keys - Navigate menu items")
        print("  Enter          - Execute selected item")
        print("  1-5            - Direct menu selection")
        print("  0              - Exit application")
        print()
        print("Control:")
        print("  Esc, Ctrl+C, q - Exit application")
        print("  h, ?           - Show/hide help")
        print("  c              - Clear results")
        print("  r              - Refresh display")
        print()
        print("Menu Items:")
        print("  1. Test Connections")
        print("  2. Search Symbols & Check Contracts")
        print("  3. Download Historical Data")
        print("  4. View TimescaleDB Data")
        print("  5. Initialize/Setup Database")
        print("  0. Exit")
    
    def _track_performance(self, frame_time: float):
        """Track display performance"""
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_frame_history:
            self.frame_times.pop(0)
        
        self.update_counter += 1
        self.last_update = time.time()
    
    def get_performance_stats(self) -> dict:
        """Get display performance statistics"""
        if not self.frame_times:
            return {}
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        max_frame_time = max(self.frame_times)
        min_frame_time = min(self.frame_times)
        
        return {
            'avg_frame_time': avg_frame_time,
            'max_frame_time': max_frame_time,
            'min_frame_time': min_frame_time,
            'avg_fps': 1.0 / avg_frame_time if avg_frame_time > 0 else 0,
            'update_counter': self.update_counter,
            'last_update': self.last_update,
            'display_mode': self.display_mode
        }
    
    def adjust_refresh_rate(self, target_fps: int):
        """Adjust refresh rate based on performance"""
        if 1 <= target_fps <= 60:
            self.refresh_rate = target_fps
            logger.info(f"Refresh rate adjusted to {target_fps} FPS")
    
    def force_refresh(self):
        """Force a display refresh"""
        if self.live_display and RICH_AVAILABLE and self.layout:
            try:
                # Update all panels to ensure everything is refreshed
                if hasattr(self, 'menu_items'):
                    self._update_all_panels(self.menu_items)
            except Exception as e:
                logger.error(f"Error during force refresh: {e}")
    
    def shutdown(self):
        """Shutdown display manager"""
        self.running = False
        if self.live_display:
            try:
                # Clean shutdown of live display
                pass
            except Exception as e:
                logger.warning(f"Display shutdown error: {e}")
    
    def get_status_info(self) -> dict:
        """Get display manager status"""
        return {
            'display_mode': self.display_mode,
            'rich_available': RICH_AVAILABLE,
            'refresh_rate': self.refresh_rate,
            'running': self.running,
            'show_results': self.show_results,
            'show_help': self.show_help,
            'current_menu_item': self.current_menu_item,
            'update_counter': self.update_counter,
            'performance': self.get_performance_stats()
        }

class ProgressTracker:
    """Separate class for tracking and displaying progress"""
    
    def __init__(self):
        self.active_downloads = {}
        self.completed_downloads = {}
        self.start_time = None
        self.running = True  # Add running flag
        
    def start_download(self, key: str, contract: str, data_type: str, total_chunks: int):
        """Start tracking a new download"""
        from admin_core_classes import DownloadProgress
        
        self.active_downloads[key] = DownloadProgress(
            contract=contract,
            data_type=data_type,
            total_chunks=total_chunks,
            completed_chunks=0,
            current_chunk_info="Starting download...",
            total_records=0,
            start_time=datetime.now()
        )
        
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def update_progress(self, key: str, completed_chunks: int, current_chunk_info: str, records_count: int = 0):
        """Update progress for a download"""
        if key in self.active_downloads:
            progress = self.active_downloads[key]
            progress.completed_chunks = completed_chunks
            progress.current_chunk_info = current_chunk_info
            progress.total_records += records_count
    
    def complete_download(self, key: str):
        """Mark a download as completed"""
        if key in self.active_downloads:
            progress = self.active_downloads[key]
            progress.completed_chunks = progress.total_chunks
            progress.current_chunk_info = "Completed"
            
            self.completed_downloads[key] = progress
            del self.active_downloads[key]
    
    def get_all_progress(self) -> dict:
        """Get all progress information"""
        all_progress = {}
        all_progress.update(self.active_downloads)
        all_progress.update(self.completed_downloads)
        return all_progress
    
    def is_active(self) -> bool:
        """Check if any downloads are active"""
        return len(self.active_downloads) > 0
    
    def clear_completed(self):
        """Clear completed downloads from tracking"""
        self.completed_downloads.clear()
    
    def get_summary(self) -> dict:
        """Get summary statistics"""
        total_active = len(self.active_downloads)
        total_completed = len(self.completed_downloads)
        
        if self.start_time:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
        else:
            elapsed_time = 0
            
        return {
            'active_downloads': total_active,
            'completed_downloads': total_completed,
            'total_downloads': total_active + total_completed,
            'elapsed_time': elapsed_time,
            'start_time': self.start_time
        }
            
    def _create_simple_display(self, menu_items: List[str]):
        """Create a simple text-based display for progress tracking"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== Progress Tracker ===")
        
        # Display active downloads
        if self.active_downloads:
            print("\nActive Downloads:")
            for key, progress in self.active_downloads.items():
                percent = (progress.completed_chunks / progress.total_chunks) * 100 if progress.total_chunks > 0 else 0
                print(f"{progress.contract} ({progress.data_type}): {percent:.1f}% - {progress.current_chunk_info}")
        
        # Display completed downloads
        if self.completed_downloads:
            print("\nCompleted Downloads:")
            for key, progress in self.completed_downloads.items():
                print(f"{progress.contract} ({progress.data_type}): Complete - {progress.total_records} records")
        
        # Display menu
        print("\n=== Menu ===")
        for i, item in enumerate(menu_items):
            print(f"{i+1}. {item}")
        
        print("\nPress the number key to select an option, or 'q' to quit")
        
    def _create_help_display(self):
        """Create help display layout"""
        if not RICH_AVAILABLE:
            return None
        
        help_content = """
[bold cyan]🎯 Keyboard Shortcuts[/bold cyan]

[bold yellow]Navigation:[/bold yellow]
• [bold]↑/↓ Arrow Keys[/bold]: Navigate menu items
• [bold]Enter[/bold]: Execute selected menu item
• [bold]1-5[/bold]: Direct menu selection
• [bold]0[/bold]: Exit application

[bold yellow]Control:[/bold yellow]
• [bold]Esc[/bold]: Exit application
• [bold]Ctrl+C[/bold]: Force exit
• [bold]q[/bold]: Quit application
• [bold]h[/bold] or [bold]?[/bold]: Show/hide this help
• [bold]c[/bold]: Clear results
• [bold]r[/bold]: Refresh display

[bold yellow]Menu Items:[/bold yellow]
1. Test Connections (DB + Rithmic)
2. Search Symbols & Check Contracts
3. Download Historical Data
4. View TimescaleDB Data
5. Initialize/Setup Database
0. Exit

[dim]Press any key to return to main menu[/dim]
        """
        
        from rich.layout import Layout
        layout = Layout()
        
        layout.split_column(
            Layout(Panel(
                Align.center(Text("RITHMIC DATA ADMIN TOOL - HELP", style="bold cyan")),
                border_style="cyan"
            ), size=3),
            Layout(Panel(help_content, title="Help", border_style="yellow")),
            Layout(Panel(
                Align.center("Press any key to return to main menu"),
                border_style="dim"
            ), size=3)
        )
        
        return layout
    
    async def run_simple_display(self, menu_items: List[str]):
        """Run simple text-based display"""
        while self.running:
            try:
                self._create_simple_display(menu_items)
                
                # Simple display doesn't auto-refresh, just wait
                await asyncio.sleep(0.5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Simple display error: {e}")
                await asyncio.sleep(1)
                
        return True