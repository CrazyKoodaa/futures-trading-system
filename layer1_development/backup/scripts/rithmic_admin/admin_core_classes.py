"""
Core classes and data structures for the Enhanced Rithmic Admin Tool
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Rich TUI library for modern interface
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.text import Text
    from rich.align import Align
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Keyboard input handling
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

logger = logging.getLogger("rithmic_admin")

@dataclass
class DownloadProgress:
    """Track download progress for each data type"""
    contract: str
    data_type: str  # 'second' or 'minute'
    total_chunks: int
    completed_chunks: int
    current_chunk_info: str
    total_records: int
    start_time: datetime
    
    @property
    def progress_percent(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100

@dataclass
class SystemStatus:
    """System status information"""
    rithmic_connected: bool = False
    db_connected: bool = False
    current_symbols: List[str] = field(default_factory=list)
    current_exchange: str = "CME"
    available_contracts: Dict[str, List[str]] = field(default_factory=dict)
    download_progress: Dict[str, DownloadProgress] = field(default_factory=dict)
    log_messages: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        # Default factories handle initialization now
        pass
        
    def add_log_message(self, message: str):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format the message for the log panel
        formatted_message = f"[{timestamp}] {message}"
        
        # Insert at the beginning for newest-first display
        # This ensures new messages appear at the top immediately
        self.log_messages.insert(0, formatted_message)
        
        # Keep only the last 100 messages to prevent memory issues
        if len(self.log_messages) > 100:
            self.log_messages = self.log_messages[:100]

class TUIComponents:
    """TUI Component creation methods"""
    
    def __init__(self, status: SystemStatus):
        self.status = status
    
    def create_status_panel(self) -> Panel:
        """Create status panel showing connection status"""
        if not RICH_AVAILABLE:
            return None
            
        # Connection status
        rithmic_status = "🟢 Connected" if self.status.rithmic_connected else "🔴 Disconnected"
        db_status = "🟢 Connected" if self.status.db_connected else "🔴 Disconnected"
        
        # Symbols and contracts
        symbols_text = ", ".join(self.status.current_symbols) if self.status.current_symbols else "None"
        
        contracts_text = []
        for symbol, contracts in self.status.available_contracts.items():
            contracts_text.append(f"{symbol}: {', '.join(contracts[:2])}")  # Show first 2 contracts
        contracts_display = " | ".join(contracts_text) if contracts_text else "None"
        
        status_text = f"""Rithmic: {rithmic_status}
Database: {db_status}
Exchange: {self.status.current_exchange}
Symbols: {symbols_text}
Contracts: {contracts_display}"""
        
        return Panel(status_text, title="System Status", border_style="blue")
    
    def create_progress_panel(self) -> Panel:
        """Create progress panel showing download progress with live updates"""
        if not RICH_AVAILABLE or not self.status.download_progress:
            return None
            
        table = Table(show_header=True, header_style="bold magenta", title="Live Download Progress")
        table.add_column("Contract", style="cyan", width=10)
        table.add_column("Type", style="green", width=8)
        table.add_column("Progress", style="yellow", width=25)
        table.add_column("Chunks", style="blue", width=8)
        table.add_column("Records", style="red", width=10)
        table.add_column("Current Chunk", style="white", width=25)
        table.add_column("Status", style="magenta", width=12)
        
        for key, progress in self.status.download_progress.items():
            # Create visual progress bar
            filled_blocks = int(progress.progress_percent / 5)  # 20 blocks total for 100%
            progress_bar = f"[green]{'█' * filled_blocks}[/green][dim]{'░' * (20 - filled_blocks)}[/dim]"
            progress_text = f"{progress_bar} {progress.progress_percent:.1f}%"
            
            # Determine status
            if progress.completed_chunks >= progress.total_chunks:
                status = "[green]✅ Complete[/green]"
            elif progress.current_chunk_info.startswith("Error"):
                status = "[red]❌ Error[/red]"
            elif "Saving" in progress.current_chunk_info:
                status = "[yellow]💾 Saving[/yellow]"
            else:
                status = "[blue]⬇️ Downloading[/blue]"
            
            table.add_row(
                progress.contract,
                progress.data_type.title(),
                progress_text,
                f"{progress.completed_chunks}/{progress.total_chunks}",
                f"{progress.total_records:,}",
                progress.current_chunk_info[:25] + "..." if len(progress.current_chunk_info) > 25 else progress.current_chunk_info,
                status
            )
        
        return Panel(table, title="📊 Download Progress", border_style="green")
    
    def create_menu_panel(self, current_item: int, menu_items: List[str]) -> Panel:
        """Create menu panel with cursor navigation"""
        if not RICH_AVAILABLE:
            return None
            
        menu_text = "[bold yellow]Main Menu[/bold yellow]\n\n"
        
        for i, item in enumerate(menu_items):
            if i == current_item:
                menu_text += f"[bold cyan]→ {i+1 if i < 5 else 0}. {item}[/bold cyan]\n"
            else:
                menu_text += f"  {i+1 if i < 5 else 0}. {item}\n"
        
        menu_text += "\n[dim]Use ↑↓ arrows to navigate, Enter to select, or type number[/dim]"
        
        return Panel(menu_text, title="Navigation", border_style="yellow")
    
    def create_results_panel(self, results_content: str, show_results: bool) -> Panel:
        """Create results panel for displaying operation results"""
        if not RICH_AVAILABLE or not show_results:
            return None
            
        if results_content:
            return Panel(
                Markdown(results_content), 
                title="📊 Results", 
                border_style="green",
                height=15
            )
        else:
            return Panel(
                "[dim]Results will appear here after operations[/dim]", 
                title="📊 Results", 
                border_style="dim"
            )
            
    def create_log_panel(self) -> Panel:
        """Create log panel for displaying system messages"""
        if not RICH_AVAILABLE:
            return None
            
        if not self.status.log_messages:
            log_content = "[dim]System messages will appear here[/dim]"
        else:
            # Display the most recent messages (already in newest-first order)
            # Take up to 10 messages to display
            display_messages = self.status.log_messages[:10]
            log_content = "\n".join(display_messages)
            
        return Panel(
            log_content,
            title="📝 System Log (Newest First)",
            border_style="blue",
            height=12
        )
    
    def create_main_layout(self, current_menu_item: int, menu_items: List[str], 
                          results_content: str, show_results: bool):
        """Create the main layout for Live display"""
        if not RICH_AVAILABLE:
            return None
            
        try:
            # Create layout
            layout = Layout()
            
            if show_results:
                # 5-panel layout when showing results (with log panel)
                layout.split_column(
                    Layout(name="header", size=6),
                    Layout(name="body", ratio=2),
                    Layout(name="results", ratio=1),
                    Layout(name="log", size=12),  # New log panel
                    Layout(name="footer", size=3)
                )
                
                results_panel = self.create_results_panel(results_content, show_results)
                if results_panel:
                    layout["results"].update(results_panel)
            else:
                # 4-panel layout without results (with log panel)
                layout.split_column(
                    Layout(name="header", size=6),
                    Layout(name="body", ratio=2),
                    Layout(name="log", size=12),  # New log panel
                    Layout(name="footer", size=3)
                )
            
            # Header with title
            layout["header"].update(
                Panel(
                    Align.center(
                        Text("RITHMIC DATA ADMIN TOOL", style="bold cyan"),
                        vertical="middle"
                    ),
                    border_style="cyan"
                )
            )
            
            # Body with status, progress, and menu
            status_panel = self.create_status_panel()
            progress_panel = self.create_progress_panel()
            menu_panel = self.create_menu_panel(current_menu_item, menu_items)
            
            # Create body layout
            if status_panel and menu_panel:
                if progress_panel:
                    # Create a nested layout for status and progress
                    status_progress_layout = Layout()
                    status_progress_layout.split_column(
                        Layout(name="status_panel", size=8),
                        Layout(name="progress_panel", size=12)
                    )
                    
                    # Update the nested layouts
                    status_progress_layout["status_panel"].update(status_panel)
                    status_progress_layout["progress_panel"].update(progress_panel)
                    
                    # Split the body into status/progress and menu
                    layout["body"].split_row(
                        Layout(status_progress_layout, ratio=1),
                        Layout(menu_panel, ratio=1)
                    )
                else:
                    # Split the body into status and menu
                    layout["body"].split_row(
                        Layout(status_panel, ratio=1),
                        Layout(menu_panel, ratio=1)
                    )
            else:
                # Fallback if panels aren't created properly
                layout["body"].update(
                    Panel("Menu and status information will appear here", title="System Status")
                )
            
            # Log panel
            log_panel = self.create_log_panel()
            if log_panel:
                layout["log"].update(log_panel)
            else:
                layout["log"].update(Panel("Log messages will appear here", title="System Log"))
            
            # Footer
            layout["footer"].update(
                Panel(
                    Align.center("🎯 Enhanced Rithmic Admin Tool • Press Ctrl+C to exit"),
                    border_style="dim"
                )
            )
            
            return layout
            
        except Exception as e:
            # If there's an error creating the layout, return a simple fallback layout
            fallback_layout = Layout()
            fallback_layout.update(
                Panel(
                    f"Error creating layout: {e}\n\nPlease check the logs for more information.",
                    title="Error",
                    border_style="red"
                )
            )
            return fallback_layout