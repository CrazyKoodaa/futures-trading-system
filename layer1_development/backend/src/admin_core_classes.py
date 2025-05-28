"""
Core data structures and TUI components for the Rithmic Admin Tool

This module provides the foundational classes for the rich TUI interface:
- Data classes for system state management
- TUI component builders using the rich library
- Layout management and styling constants
- Menu configuration and navigation support

Author: Futures Trading System
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Rich library components for TUI
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.layout import Layout
from rich.align import Align
from rich.console import Console, Group
from rich.rule import Rule
from rich.tree import Tree


class LayoutType(Enum):
    """Layout configuration types for the TUI"""
    THREE_PANEL = "3panel"
    FOUR_PANEL = "4panel"
    FULL_SCREEN = "fullscreen"


class ColorScheme:
    """Color scheme constants for consistent styling"""
    # Status colors
    SUCCESS = "green"
    ERROR = "red" 
    WARNING = "yellow"
    INFO = "cyan"
    NEUTRAL = "white"
    
    # UI element colors
    HEADER = "bold blue"
    MENU_SELECTED = "bold green on black"
    MENU_NORMAL = "white"
    PANEL_BORDER = "blue"
    PROGRESS_BAR = "green"
    
    # Data display colors
    SYMBOL = "bold yellow"
    EXCHANGE = "cyan"
    CONTRACT = "magenta"
    TIMESTAMP = "dim white"


# Menu configuration - Updated for modular structure
MENU_ITEMS = [
    {'title': "Test Connections (DB + Rithmic)", 'key': 'test_connections'},
    {'title': "Search Symbols & Check Contracts", 'key': 'search_symbols'}, 
    {'title': "Download Historical Data", 'key': 'download_historical'},
    {'title': "View TimescaleDB Data", 'key': 'view_data'},
    {'title': "Initialize/Setup Database", 'key': 'setup_database'},
    {'title': "Connection Management", 'key': 'manage_connections'},
    {'title': "Symbol Explorer", 'key': 'explore_symbols'},
    {'title': "Data Export Tools", 'key': 'export_data'},
    {'title': "Exit", 'key': 'exit'}
]

MENU_DESCRIPTIONS = [
    "Verify database and Rithmic API connections",
    "Search for trading symbols and validate contracts",
    "Download historical market data to TimescaleDB",
    "Browse stored market data and statistics",
    "Set up database schema and extensions",
    "Advanced connection settings and diagnostics",
    "Interactive symbol browser and contract explorer",
    "Export data to various formats (CSV, JSON, Parquet)",
    "Quit the admin tool"
]

# Module-specific menus
CONNECTION_MENU_ITEMS = [
    "Test Connection Status",
    "Connection Diagnostics", 
    "Reconnect to Rithmic",
    "Connection Settings",
    "Plant Status",
    "Back to Main Menu"
]

SYMBOLS_MENU_ITEMS = [
    "Search Symbols",
    "Browse by Exchange",
    "View Contract Details",
    "Front Month Finder",
    "Symbol Favorites",
    "Export Symbol List",
    "Back to Main Menu"
]

HISTORICAL_MENU_ITEMS = [
    "Quick Download (Last 7 Days)",
    "Custom Date Range",
    "Bulk Symbol Download",
    "Resume Interrupted Download",
    "Download Statistics",
    "Data Validation",
    "Back to Main Menu"
]


@dataclass
class DownloadProgress:
    """Progress tracking for data download operations"""
    symbol: str
    current_operation: str = ""
    total_chunks: int = 0
    completed_chunks: int = 0
    current_timeframe: str = ""
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    bytes_downloaded: int = 0
    records_processed: int = 0
    error_count: int = 0
    operation_type: str = ""  # 'historical', 'symbols', 'connection'
    contract: str = ""
    exchange: str = ""
    
    # Additional attributes used by other modules
    records_downloaded: int = 0
    current_step: int = 0
    completion_percentage: float = 0.0
    error: str = ""
    progress: float = 0.0
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Calculate elapsed time since start"""
        if self.start_time is None:
            return None
        return datetime.now() - self.start_time
    
    @property
    def download_complete(self) -> bool:
        """Check if download is complete"""
        return self.total_chunks > 0 and self.completed_chunks >= self.total_chunks
    
    def update_chunk(self, increment: int = 1) -> None:
        """Update completed chunks count"""
        self.completed_chunks = min(self.completed_chunks + increment, self.total_chunks)
    
    def reset(self) -> None:
        """Reset progress tracking"""
        self.current_operation = ""
        self.total_chunks = 0
        self.completed_chunks = 0
        self.current_timeframe = ""
        self.start_time = None
        self.estimated_completion = None
        self.bytes_downloaded = 0
        self.records_processed = 0
        self.error_count = 0


@dataclass
class SystemStatus:
    """Global system status tracking"""
    rithmic_connected: bool = False
    database_connected: bool = False
    current_symbols: List[str] = field(default_factory=list)
    current_exchange: str = "CME"
    available_contracts: Dict[str, List[str]] = field(default_factory=dict)
    download_progress: Dict[str, DownloadProgress] = field(default_factory=dict)
    last_operation_result: str = ""
    last_error: str = ""
    operation_count: int = 0
    session_start_time: datetime = field(default_factory=datetime.now)
    
    # New fields for modular operations
    active_operations: Dict[str, str] = field(default_factory=dict)  # operation_id -> status
    connection_details: Dict[str, Any] = field(default_factory=dict)
    symbol_search_results: List[Dict[str, Any]] = field(default_factory=list)
    historical_data_stats: Dict[str, Any] = field(default_factory=dict)
    current_module: str = "main"  # Track which module is active
    
    # Additional attributes used by AdminOperations
    db_connected: bool = False
    rithmic_gateway: str = ""
    rithmic_user: str = ""
    
    @property
    def connection_status(self) -> str:
        """Get overall connection status"""
        if self.rithmic_connected and self.database_connected:
            return "All Connected"
        elif self.rithmic_connected:
            return "Rithmic Only"
        elif self.database_connected:
            return "Database Only"
        else:
            return "Disconnected"
    
    @property
    def session_duration_time(self) -> timedelta:
        """Get current session duration"""
        return datetime.now() - self.session_start_time
    
    def add_symbol(self, symbol: str) -> None:
        """Add symbol to current list"""
        if symbol not in self.current_symbols:
            self.current_symbols.append(symbol)
    
    def remove_symbol(self, symbol: str) -> None:
        """Remove symbol from current list"""
        if symbol in self.current_symbols:
            self.current_symbols.remove(symbol)
    
    def clear_symbols(self) -> None:
        """Clear all current symbols"""
        self.current_symbols.clear()
        self.available_contracts.clear()
        self.download_progress.clear()
    
    def update_operation_status(self, operation_id: str, status: str) -> None:
        """Update status of active operation"""
        self.active_operations[operation_id] = status
    
    def clear_operation(self, operation_id: str) -> None:
        """Clear completed operation"""
        self.active_operations.pop(operation_id, None)
    
    def set_active_module(self, module_name: str) -> None:
        """Set currently active module"""
        self.current_module = module_name


@dataclass
class RithmicConnectionInfo:
    """Rithmic connection details and capabilities"""
    gateway: str = ""
    server_name: str = ""
    user: str = ""
    app_name: str = ""
    app_version: str = ""
    connected_plants: List[str] = field(default_factory=list)
    connection_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    connection_stable: bool = False
    error_count: int = 0
    reconnect_attempts: int = 0


@dataclass
class SymbolSearchResult:
    """Symbol search result structure"""
    symbol: str
    product_code: str
    exchange: str
    instrument_type: str
    expiration_date: Optional[datetime] = None
    symbol_name: str = ""
    tick_size: Optional[float] = None
    point_value: Optional[float] = None
    currency: str = "USD"
    is_active: bool = True
    front_month: bool = False


@dataclass 
class HistoricalDataRequest:
    """Historical data request configuration"""
    symbols: List[str]
    exchanges: List[str]
    start_date: datetime
    end_date: datetime
    timeframes: List[str] = field(default_factory=lambda: ["1s", "1m", "5m", "15m", "1h", "1d"])
    data_types: List[str] = field(default_factory=lambda: ["bars", "ticks"])
    max_records_per_request: int = 10000
    delay_between_requests: float = 0.1
    save_to_database: bool = True
    save_to_files: bool = False


@dataclass
class DatabaseStats:
    """Database statistics for display"""
    table_name: str
    record_count: int = 0
    latest_timestamp: Optional[datetime] = None
    earliest_timestamp: Optional[datetime] = None
    symbols: List[str] = field(default_factory=list)
    exchanges: List[str] = field(default_factory=list)
    size_mb: float = 0.0
    
    @property
    def date_range_str(self) -> str:
        """Get formatted date range string"""
        if not self.earliest_timestamp or not self.latest_timestamp:
            return "No data"
        return f"{self.earliest_timestamp.strftime('%Y-%m-%d')} to {self.latest_timestamp.strftime('%Y-%m-%d')}"


class TUIComponents:
    """Rich TUI component factory for the admin interface"""
    
    def __init__(self, system_status: SystemStatus):
        """Initialize with system status reference"""
        self.system_status = system_status
        self.console = Console()
    
    def create_header_panel(self, **_unused_kwargs) -> Panel:
        """Create the main header panel with system status"""
        # Connection status indicators
        rithmic_status = Text("●", style=ColorScheme.SUCCESS if self.system_status.rithmic_connected else ColorScheme.ERROR)
        db_status = Text("●", style=ColorScheme.SUCCESS if self.system_status.database_connected else ColorScheme.ERROR)
        
        # Header content
        header_content = Group(
            Text("RITHMIC FUTURES TRADING ADMIN TOOL", style=ColorScheme.HEADER, justify="center"),
            Rule(style=ColorScheme.PANEL_BORDER),
            Columns([
                Text(f"Rithmic {rithmic_status.plain} {'Connected' if self.system_status.rithmic_connected else 'Disconnected'}", 
                     style=ColorScheme.SUCCESS if self.system_status.rithmic_connected else ColorScheme.ERROR),
                Text(f"Database {db_status.plain} {'Connected' if self.system_status.database_connected else 'Disconnected'}", 
                     style=ColorScheme.SUCCESS if self.system_status.database_connected else ColorScheme.ERROR),
                Text(f"Session: {self._format_time_duration(self.system_status.session_duration_time)}", 
                     style=ColorScheme.INFO)
            ], equal=True)
        )
        
        return Panel(
            header_content,
            title="System Status",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(0, 1)
        )
    
    def create_menu_panel(self, selected_index: int = 0) -> Panel:
        """Create the main menu panel with navigation"""
        menu_items = []
        
        for i, (item, description) in enumerate(zip(MENU_ITEMS, MENU_DESCRIPTIONS)):
            menu_title = item['title'] if isinstance(item, dict) else item
            
            if i == selected_index:
                # Highlighted selected item
                menu_items.append(
                    Text(f"► {i+1}. {menu_title}", style=ColorScheme.MENU_SELECTED)
                )
                menu_items.append(
                    Text(f"   {description}", style="dim " + ColorScheme.MENU_SELECTED)
                )
            else:
                # Normal menu item
                menu_items.append(
                    Text(f"  {i+1}. {menu_title}", style=ColorScheme.MENU_NORMAL)
                )
                menu_items.append(
                    Text(f"   {description}", style="dim white")
                )
            
            # Add spacing between items
            if i < len(MENU_ITEMS) - 1:
                menu_items.append(Text(""))
        
        menu_content = Group(*menu_items)
        
        return Panel(
            menu_content,
            title="Main Menu",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 2)
        )
    
    def create_status_panel(self) -> Panel:
        """Create the current system status display panel"""
        status_table = Table.grid(padding=(0, 1))
        status_table.add_column("Label", style="bold")
        status_table.add_column("Value")
        
        # Exchange and symbols
        status_table.add_row("Exchange:", Text(self.system_status.current_exchange, style=ColorScheme.EXCHANGE))
        
        if self.system_status.current_symbols:
            symbols_text = ", ".join(self.system_status.current_symbols)
            status_table.add_row("Symbols:", Text(symbols_text, style=ColorScheme.SYMBOL))
        else:
            status_table.add_row("Symbols:", Text("None selected", style="dim white"))
        
        # Available contracts
        if self.system_status.available_contracts:
            contracts_info = []
            for symbol, contracts in self.system_status.available_contracts.items():
                contracts_info.append(f"{symbol}: {len(contracts)} contracts")
            status_table.add_row("Contracts:", Text(" | ".join(contracts_info), style=ColorScheme.CONTRACT))
        
        # Last operation
        if self.system_status.last_operation_result:
            status_table.add_row("Last Result:", Text(self.system_status.last_operation_result, style=ColorScheme.INFO))
        
        # Error status
        if self.system_status.last_error:
            status_table.add_row("Last Error:", Text(self.system_status.last_error, style=ColorScheme.ERROR))
        
        return Panel(
            status_table,
            title="Current Status",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
    
    def create_results_panel(self, content: str = "", title: str = "Results") -> Panel:
        """Create results display panel with markdown support"""
        if not content:
            content = "*No results to display*"
        
        # Try to render as markdown, fall back to plain text
        try:
            if content.startswith("```") or "**" in content or "*" in content:
                result_content = Markdown(content)
            else:
                result_content = Text(content, style=ColorScheme.NEUTRAL)
        except Exception:
            result_content = Text(content, style=ColorScheme.NEUTRAL)
        
        return Panel(
            result_content,
            title=title,
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1),
            height=15
        )
    
    def create_progress_panel(self) -> Panel:
        """Create live progress tracking panel"""
        if not self.system_status.download_progress:
            return Panel(
                Text("No active operations", style="dim white", justify="center"),
                title="Progress",
                border_style=ColorScheme.PANEL_BORDER,
                padding=(1, 1)
            )
        
        progress_items = []
        
        for symbol, progress in self.system_status.download_progress.items():
            # Progress bar for each symbol
            if progress.total_chunks > 0:
                progress_bar = self._create_progress_bar(progress)
                progress_items.append(progress_bar)
            
            # Operation details
            if progress.current_operation:
                operation_text = Text(f"{symbol}: {progress.current_operation}", style=ColorScheme.INFO)
                progress_items.append(operation_text)
            
            # Timeframe info
            if progress.current_timeframe:
                timeframe_text = Text(f"  Timeframe: {progress.current_timeframe}", style="dim white")
                progress_items.append(timeframe_text)
            
            # Statistics
            if progress.records_processed > 0:
                stats_text = Text(f"  Records: {progress.records_processed:,}", style="dim white")
                progress_items.append(stats_text)
            
            # Error count
            if progress.error_count > 0:
                error_text = Text(f"  Errors: {progress.error_count}", style=ColorScheme.WARNING)
                progress_items.append(error_text)
            
            progress_items.append(Text(""))  # Spacing
        
        return Panel(
            Group(*progress_items),
            title="Progress Tracking",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
    
    def create_connection_status_panel(self, connection_info: Optional[RithmicConnectionInfo] = None) -> Panel:
        """Create detailed connection status panel"""
        if not connection_info:
            return Panel(
                Text("No connection information available", style="dim white", justify="center"),
                title="Connection Details",
                border_style=ColorScheme.PANEL_BORDER
            )
        
        conn_table = Table.grid(padding=(0, 1))
        conn_table.add_column("Label", style="bold")
        conn_table.add_column("Value")
        
        conn_table.add_row("Gateway:", Text(connection_info.gateway, style=ColorScheme.INFO))
        conn_table.add_row("Server:", Text(connection_info.server_name, style=ColorScheme.INFO))
        conn_table.add_row("User:", Text(connection_info.user, style=ColorScheme.SYMBOL))
        conn_table.add_row("App:", Text(f"{connection_info.app_name} v{connection_info.app_version}", style="white"))
        
        if connection_info.connected_plants:
            plants_text = ", ".join(connection_info.connected_plants)
            conn_table.add_row("Plants:", Text(plants_text, style=ColorScheme.SUCCESS))
        
        if connection_info.connection_time:
            duration = datetime.now() - connection_info.connection_time
            conn_table.add_row("Connected:", Text(self._format_time_duration(duration), style=ColorScheme.INFO))
        
        conn_table.add_row("Stable:", Text(
            "Yes" if connection_info.connection_stable else "No",
            style=ColorScheme.SUCCESS if connection_info.connection_stable else ColorScheme.WARNING
        ))
        
        if connection_info.error_count > 0:
            conn_table.add_row("Errors:", Text(str(connection_info.error_count), style=ColorScheme.ERROR))
        
        return Panel(
            conn_table,
            title="Connection Details",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
    
    def create_symbol_search_panel(self, search_results: List[SymbolSearchResult]) -> Panel:
        """Create symbol search results panel"""
        if not search_results:
            return Panel(
                Text("No search results", style="dim white", justify="center"),
                title="Symbol Search Results",
                border_style=ColorScheme.PANEL_BORDER
            )
        
        results_table = Table()
        results_table.add_column("Symbol", style=ColorScheme.SYMBOL)
        results_table.add_column("Exchange", style=ColorScheme.EXCHANGE)
        results_table.add_column("Type", style="white")
        results_table.add_column("Expiration", style="dim white")
        results_table.add_column("Front", justify="center")
        
        for result in search_results[:20]:  # Limit display
            front_indicator = "●" if result.front_month else "○"
            front_style = ColorScheme.SUCCESS if result.front_month else "dim white"
            
            results_table.add_row(
                result.symbol,
                result.exchange,
                result.instrument_type,
                result.expiration_date.strftime("%Y-%m-%d") if result.expiration_date else "N/A",
                Text(front_indicator, style=front_style)
            )
        
        if len(search_results) > 20:
            footer_text = f"Showing 20 of {len(search_results)} results"
        else:
            footer_text = f"{len(search_results)} results found"
        
        return Panel(
            Group(results_table, Text(footer_text, style="dim white", justify="center")),
            title="Symbol Search Results",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
    
    def create_operations_panel(self) -> Panel:
        """Create active operations monitoring panel"""
        if not self.system_status.active_operations:
            return Panel(
                Text("No active operations", style="dim white", justify="center"),
                title="Active Operations",
                border_style=ColorScheme.PANEL_BORDER
            )
        
        ops_table = Table()
        ops_table.add_column("Operation", style="bold")
        ops_table.add_column("Status", style="white")
        ops_table.add_column("Module", style=ColorScheme.INFO)
        
        for op_id, status in self.system_status.active_operations.items():
            # Extract module from operation ID if formatted as module:operation
            if ":" in op_id:
                module, operation = op_id.split(":", 1)
            else:
                module = "core"
                operation = op_id
            
            status_style = ColorScheme.SUCCESS if "completed" in status.lower() else ColorScheme.INFO
            if "error" in status.lower() or "failed" in status.lower():
                status_style = ColorScheme.ERROR
            
            ops_table.add_row(
                operation,
                Text(status, style=status_style),
                module
            )
        
        return Panel(
            ops_table,
            title="Active Operations",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
        
    def create_database_statistics_panel(self, stats: Optional[List[DatabaseStats]] = None) -> Panel:
        """Create database statistics display panel"""
        if not stats:
            return Panel(
                Text("No database statistics available", style="dim white", justify="center"),
                title="Database Statistics",
                border_style=ColorScheme.PANEL_BORDER,
                padding=(1, 1)
            )
        
        stats_table = Table()
        stats_table.add_column("Table", style="bold")
        stats_table.add_column("Records", justify="right")
        stats_table.add_column("Date Range", style="dim")
        stats_table.add_column("Symbols", justify="center")
        stats_table.add_column("Size (MB)", justify="right")
        
        for stat in stats:
            stats_table.add_row(
                stat.table_name,
                f"{stat.record_count:,}",
                stat.date_range_str,
                str(len(stat.symbols)),
                f"{stat.size_mb:.1f}"
            )
        
        return Panel(
            stats_table,
            title="Database Statistics",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
    
    def create_module_menu_panel(self, module_name: str, selected_index: int = 0) -> Panel:
        """Create module-specific menu panel"""
        menu_items = []
        descriptions = []
        
        if module_name == "connection":
            menu_items = CONNECTION_MENU_ITEMS
            descriptions = [
                "Check current connection status and health",
                "Run detailed connection diagnostics",
                "Attempt to reconnect to Rithmic servers",
                "Configure connection parameters",
                "View connected plant status",
                "Return to main menu"
            ]
        elif module_name == "symbols":
            menu_items = SYMBOLS_MENU_ITEMS  
            descriptions = [
                "Search for symbols by name or pattern",
                "Browse symbols by exchange",
                "View detailed contract information",
                "Find front month contracts automatically",
                "Manage favorite symbols list",
                "Export symbol data to file",
                "Return to main menu"
            ]
        elif module_name == "historical":
            menu_items = HISTORICAL_MENU_ITEMS
            descriptions = [
                "Download last 7 days of data quickly",
                "Specify custom date range for download",
                "Download data for multiple symbols",
                "Continue a previously interrupted download",
                "View download statistics and metrics",
                "Validate downloaded data integrity",
                "Return to main menu"
            ]
        else:
            # Fallback to main menu
            menu_items = MENU_ITEMS
            descriptions = MENU_DESCRIPTIONS
        
        menu_content = []
        
        for i, (item, description) in enumerate(zip(menu_items, descriptions)):
            if i == selected_index:
                # Highlighted selected item
                menu_content.append(
                    Text(f"► {i+1}. {item}", style=ColorScheme.MENU_SELECTED)
                )
                menu_content.append(
                    Text(f"   {description}", style="dim " + ColorScheme.MENU_SELECTED)
                )
            else:
                # Normal menu item
                menu_content.append(
                    Text(f"  {i+1}. {item}", style=ColorScheme.MENU_NORMAL)
                )
                menu_content.append(
                    Text(f"   {description}", style="dim white")
                )
            
            # Add spacing between items
            if i < len(menu_items) - 1:
                menu_content.append(Text(""))
        
        title = f"{module_name.title()} Menu" if module_name != "main" else "Main Menu"
        
        return Panel(
            Group(*menu_content),
            title=title,
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 2)
        )
    
    def create_symbol_explorer_panel(self, symbols_data: Optional[Dict] = None) -> Panel:
        """Create a tree view of symbols and their contracts"""
        if not symbols_data:
            return Panel(
                Text("No symbols available", style="dim white", justify="center"),
                title="Symbol Explorer",
                border_style=ColorScheme.PANEL_BORDER
            )
        
        tree = Tree("📊 Trading Symbols", style=ColorScheme.HEADER)
        
        for symbol, data in symbols_data.items():
            symbol_node = tree.add(f"[{ColorScheme.SYMBOL}]{symbol}[/] ({data.get('exchange', 'Unknown')})")
            
            # Add contracts
            contracts = data.get('contracts', [])
            if contracts:
                contracts_node = symbol_node.add(f"📋 Contracts ({len(contracts)})")
                for contract in contracts[:5]:  # Limit display
                    contracts_node.add(f"[{ColorScheme.CONTRACT}]{contract}[/]")
                if len(contracts) > 5:
                    contracts_node.add(f"... and {len(contracts) - 5} more")
            
            # Add data statistics
            if 'data_points' in data:
                data_node = symbol_node.add(f"📈 Data Points: {data['data_points']:,}")
            
            if 'latest_data' in data:
                latest_node = symbol_node.add(f"🕒 Latest: {data['latest_data']}")
        
        return Panel(
            tree,
            title="Symbol Explorer",
            border_style=ColorScheme.PANEL_BORDER,
            padding=(1, 1)
        )
    
    def _create_progress_bar(self, progress: DownloadProgress) -> Text:
        """Create a text-based progress bar"""
        percentage = progress.completion_percentage
        bar_width = 30
        filled_width = int((percentage / 100) * bar_width)
        
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        return Text(
            f"{progress.symbol}: [{bar}] {percentage:.1f}% ({progress.completed_chunks}/{progress.total_chunks})",
            style=ColorScheme.PROGRESS_BAR if percentage > 0 else "dim white"
        )
    
    def _format_time_duration(self, duration: timedelta) -> str:
        """Format duration for display"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
            
    def set_operation_result(self, result: Dict[str, Any]) -> None:
        """
        Set the result of an operation for display in the UI.
        
        Args:
            result: Dictionary containing operation result information
                   with keys like 'status', 'title', 'message', etc.
        """
        self.operation_result = result
        
    def update_progress_info(self, symbol: str, progress: DownloadProgress) -> None:
        """
        Update progress information for a specific symbol.
        
        Args:
            symbol: The symbol being processed
            progress: DownloadProgress object with current progress information
        """
        if not hasattr(self, 'progress_info'):
            self.progress_info = {}
            
        self.progress_info[symbol] = progress


class LayoutManager:
    """Manages TUI layout configurations and panel arrangements"""
    
    def __init__(self, layout_type: LayoutType = LayoutType.FOUR_PANEL):
        """Initialize layout manager with specified layout type"""
        self.layout_type = layout_type
        self.layout = Layout()
        self._setup_layout()
    
    def _setup_layout(self) -> None:
        """Configure the layout based on layout type"""
        if self.layout_type == LayoutType.THREE_PANEL:
            self.layout.split(
                Layout(name="header", size=5),
                Layout(name="body", ratio=1),
                Layout(name="footer", size=3)
            )
            self.layout["body"].split_row(
                Layout(name="menu", ratio=1),
                Layout(name="content", ratio=2)
            )
        
        elif self.layout_type == LayoutType.FOUR_PANEL:
            self.layout.split(
                Layout(name="header", size=6),
                Layout(name="body", ratio=1),
                Layout(name="footer", size=8)
            )
            self.layout["body"].split_row(
                Layout(name="menu", ratio=1),
                Layout(name="status", ratio=1),
                Layout(name="content", ratio=2)
            )
        
        elif self.layout_type == LayoutType.FULL_SCREEN:
            self.layout.split(
                Layout(name="content", ratio=1)
            )
    
    def get_layout(self) -> Layout:
        """Get the configured layout"""
        return self.layout
    
    def update_panel(self, panel_name: str, content: Any) -> None:
        """Update a specific panel with new content"""
        try:
            self.layout[panel_name].update(content)
        except KeyError:
            # Panel doesn't exist in current layout
            pass
    
    def get_panel_names(self) -> List[str]:
        """Get list of available panel names"""
        panel_names = []
        
        def collect_names(layout_item, names):
            if hasattr(layout_item, 'name') and layout_item.name:
                names.append(layout_item.name)
            if hasattr(layout_item, 'children'):
                for child in layout_item.children:
                    collect_names(child, names)
        
        collect_names(self.layout, panel_names)
        return panel_names


# Utility functions for the TUI system
def format_bytes(bytes_count: float) -> str:
    """Format byte count for human-readable display"""
    bytes_count_float = float(bytes_count)  # Ensure we're working with a float
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count_float < 1024.0:
            return f"{bytes_count_float:.1f} {unit}"
        bytes_count_float /= 1024.0
    return f"{bytes_count_float:.1f} TB"


def format_number(number: int) -> str:
    """Format number with thousands separators"""
    return f"{number:,}"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def get_status_color(status: bool) -> str:
    """Get color for boolean status"""
    return ColorScheme.SUCCESS if status else ColorScheme.ERROR


# Export all classes and constants
__all__ = [
    'DownloadProgress',
    'SystemStatus', 
    'DatabaseStats',
    'RithmicConnectionInfo',
    'SymbolSearchResult',
    'HistoricalDataRequest',
    'TUIComponents',
    'LayoutManager',
    'LayoutType',
    'ColorScheme',
    'MENU_ITEMS',
    'MENU_DESCRIPTIONS',
    'CONNECTION_MENU_ITEMS',
    'SYMBOLS_MENU_ITEMS', 
    'HISTORICAL_MENU_ITEMS',
    'format_bytes',
    'format_number',
    'truncate_text',
    'get_status_color'
]