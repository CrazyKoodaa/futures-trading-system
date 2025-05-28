import time
import asyncio
import logging
import re
import fnmatch
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from dataclasses import dataclass

# Rich TUI library for modern interface
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.columns import Columns
    from rich import box
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Rich library not available. Install with: pip install rich")
    print("Falling back to basic interface...")

from async_rithmic import RithmicClient, TimeBarType, InstrumentType, Gateway, DataType
from async_rithmic import ReconnectionSettings, RetrySettings
from config.chicago_gateway_config import get_chicago_gateway_config
from shared.database.connection import get_async_session, TimescaleDBHelper, get_database_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rithmic_admin.log"),
        logging.StreamHandler()
    ]
)
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
    current_symbols: List[str] = None
    current_exchange: str = "CME"
    available_contracts: Dict[str, List[str]] = None
    download_progress: Dict[str, DownloadProgress] = None
    
    def __post_init__(self):
        if self.current_symbols is None:
            self.current_symbols = []
        if self.available_contracts is None:
            self.available_contracts = {}
        if self.download_progress is None:
            self.download_progress = {}

class RithmicAdminTUI:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.status = SystemStatus()
        self.rithmic_client: Optional[RithmicClient] = None
        
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
    
    def update_progress_display(self, contract: str, data_type: str, chunk_info: str, 
                               completed: int, total: int, records: int):
        """Update progress for a specific contract and data type"""
        progress_key = f"{contract}_{data_type}"
        
        if progress_key in self.status.download_progress:
            self.status.download_progress[progress_key].current_chunk_info = chunk_info
            self.status.download_progress[progress_key].completed_chunks = completed
            self.status.download_progress[progress_key].total_chunks = total
            self.status.download_progress[progress_key].total_records = records
            
            # Update live display if available
            if hasattr(self, '_live_display') and self._live_display:
                self._live_display.update(self._create_main_layout())
    
    def display_main_menu(self):
        """Display the main menu without clearing screen"""
        if RICH_AVAILABLE:
            # Use Live display for non-clearing updates
            with Live(self._create_main_layout(), console=self.console, refresh_per_second=4) as live:
                self._live_display = live
                return live
        else:
            # Fallback for no Rich - only print header once
            if not hasattr(self, '_menu_displayed'):
                print("\n" + "="*60)
                print("RITHMIC DATA ADMIN TOOL".center(60))
                print("="*60)
                self._menu_displayed = True
            
            # Update only status lines using ANSI escape codes
            print(f"\r\033[K📡 Rithmic: {'🟢 Connected' if self.status.rithmic_connected else '🔴 Disconnected'}")
            print(f"\r\033[K💾 Database: {'🟢 Connected' if self.status.db_connected else '🔴 Disconnected'}")
            
            if not hasattr(self, '_static_menu_printed'):
                print("-"*60)
                print("1. Test Connections (DB + Rithmic)")
                print("2. Search Symbols & Check Contracts")
                print("3. Download Historical Data")
                print("4. View TimescaleDB Data")
                print("5. Initialize/Setup Database")
                print("0. Exit")
                print("-"*60)
                self._static_menu_printed = True
    
    def _create_main_layout(self):
        """Create the main layout for Live display"""
        if not RICH_AVAILABLE:
            return None
            
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=6),
            Layout(name="body"),
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
        
        # Body with status and menu
        status_panel = self.create_status_panel()
        progress_panel = self.create_progress_panel()
        
        menu_text = """[bold yellow]Main Menu[/bold yellow]

[bold cyan]1.[/bold cyan] Test Connections (DB + Rithmic)
[bold cyan]2.[/bold cyan] Search Symbols & Check Contracts  
[bold cyan]3.[/bold cyan] Download Historical Data
[bold cyan]4.[/bold cyan] View TimescaleDB Data
[bold cyan]5.[/bold cyan] Initialize/Setup Database
[bold cyan]0.[/bold cyan] Exit"""
        
        menu_panel = Panel(menu_text, title="Options", border_style="yellow")
        
        if progress_panel:
            layout["body"].split_column(
                Layout(status_panel, size=8),
                Layout(progress_panel, size=12),
                Layout(menu_panel)
            )
        else:
            layout["body"].split_column(
                Layout(status_panel, size=8),
                Layout(menu_panel)
            )
        
        # Footer
        layout["footer"].update(
            Panel(
                Align.center("Use number keys to navigate • Press Ctrl+C to exit"),
                border_style="dim"
            )
        )
        
        return layout
    
    def update_live_display(self):
        """Update the live display without clearing"""
        if hasattr(self, '_live_display') and self._live_display:
            self._live_display.update(self._create_main_layout())

    async def test_connections(self):
        """Test database and Rithmic connections"""
        if RICH_AVAILABLE:
            with self.console.status("[bold green]Testing connections...") as status:
                # Test database
                status.update("[bold blue]Testing TimescaleDB connection...")
                try:
                    db_manager = get_database_manager()
                    connection_ok = await db_manager.test_connection()
                    if connection_ok:
                        self.console.print("✅ TimescaleDB connection successful", style="green")
                        self.status.db_connected = True
                        
                        # Verify tables exist
                        async with get_async_session() as session:
                            from sqlalchemy import text
                            result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds LIMIT 1"))
                            self.console.print("✅ TimescaleDB tables accessible", style="green")
                    else:
                        self.console.print("❌ TimescaleDB connection failed", style="red")
                        self.status.db_connected = False
                except Exception as e:
                    self.console.print(f"❌ TimescaleDB connection error: {e}", style="red")
                    self.status.db_connected = False
                
                # Test Rithmic
                status.update("[bold blue]Testing Rithmic connection...")
                await self.connect_to_rithmic()
        else:
            print("Testing connections...")
            # Fallback implementation
            await self.connect_to_rithmic()
    
    async def connect_to_rithmic(self) -> bool:
        """Connect to Rithmic API"""
        try:
            config = get_chicago_gateway_config()
            
            if RICH_AVAILABLE:
                self.console.print(f"Connecting to Rithmic as {config['rithmic']['user']}...", style="blue")
            
            reconnection = ReconnectionSettings(
                max_retries=3,
                backoff_type="exponential",
                interval=2,
                max_delay=30,
                jitter_range=(0.5, 1.5)
            )
            
            retry = RetrySettings(
                max_retries=2,
                timeout=20.0,
                jitter_range=(0.5, 1.5)
            )
            
            gateway_name = config['rithmic']['gateway']
            gateway = Gateway.CHICAGO if gateway_name == 'Chicago' else Gateway.TEST
            
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
            
            await self.rithmic_client.connect()
            self.status.rithmic_connected = True
            
            if RICH_AVAILABLE:
                self.console.print("✅ Successfully connected to Rithmic!", style="green")
            else:
                print("✅ Successfully connected to Rithmic!")
            
            return True
            
        except Exception as e:
            self.status.rithmic_connected = False
            if RICH_AVAILABLE:
                self.console.print(f"❌ Failed to connect to Rithmic: {e}", style="red")
            else:
                print(f"❌ Failed to connect to Rithmic: {e}")
            return False

    async def search_symbols_and_contracts(self):
        """Search for symbols and check contracts with Rich TUI"""
        if not self.status.rithmic_connected:
            if RICH_AVAILABLE:
                self.console.print("❌ Not connected to Rithmic. Please test connections first.", style="red")
            return
        
        # Get search parameters
        if RICH_AVAILABLE:
            search_term = Prompt.ask(
                "[cyan]Enter search term[/cyan] (e.g., ES, NQ, NQ?5, NQ*)",
                default=""
            )
            
            if not search_term:
                self.console.print("❌ Search term cannot be empty", style="red")
                return
            
            exchange = Prompt.ask(
                f"[cyan]Enter exchange[/cyan]",
                default=self.status.current_exchange,
                show_default=True
            )
        else:
            search_term = input("Enter search term (e.g., ES, NQ, NQ?5, NQ*): ")
            if not search_term:
                print("❌ Search term cannot be empty")
                return
            exchange = input(f"Enter exchange (default: {self.status.current_exchange}): ") or self.status.current_exchange
        
        self.status.current_exchange = exchange
        
        # Determine if wildcards are used
        has_wildcards = '*' in search_term or '?' in search_term
        api_search_term = search_term
        
        if has_wildcards:
            api_search_term = re.split(r'[\*\?]', search_term)[0]
            if not api_search_term:
                api_search_term = search_term.replace('*', '').replace('?', '')
                if not api_search_term:
                    api_search_term = 'A'
        
        # Search for symbols
        if RICH_AVAILABLE:
            with self.console.status(f"[bold blue]Searching for '{search_term}' on {exchange}...") as status:
                try:
                    results = await self._search_symbols(api_search_term, InstrumentType.FUTURE, exchange)
                except Exception as e:
                    self.console.print(f"❌ Error searching for symbols: {e}", style="red")
                    return
        else:
            print(f"Searching for '{search_term}' on {exchange}...")
            try:
                results = await self._search_symbols(api_search_term, InstrumentType.FUTURE, exchange)
            except Exception as e:
                print(f"❌ Error searching for symbols: {e}")
                return
        
        if not results:
            if RICH_AVAILABLE:
                self.console.print(f"❌ No symbols found matching '{search_term}' on {exchange}", style="yellow")
            else:
                print(f"❌ No symbols found matching '{search_term}' on {exchange}")
            return
        
        # Filter results if wildcards are used
        filtered_results = results
        if has_wildcards:
            filtered_results = []
            pattern = search_term.replace('?', '.').replace('*', '.*')
            is_nq_es = search_term.upper().startswith('NQ') or search_term.upper().startswith('ES')
            
            for result in results:
                if is_nq_es:
                    symbol = result.symbol.upper()
                    month_code = None
                    if len(symbol) > 2:
                        for char in symbol[2:]:
                            if char.isalpha():
                                month_code = char
                                break
                    if month_code and month_code not in ['H', 'M', 'U', 'Z']:
                        continue
                
                if (re.match(pattern, result.symbol, re.IGNORECASE) or
                    re.match(pattern, result.product_code, re.IGNORECASE)):
                    filtered_results.append(result)
            
            if not filtered_results:
                if RICH_AVAILABLE:
                    self.console.print(f"❌ No symbols found matching wildcard pattern '{search_term}'", style="yellow")
                else:
                    print(f"❌ No symbols found matching wildcard pattern '{search_term}'")
                return
        
        # Display results and get user selection
        if RICH_AVAILABLE:
            selected_results = await self._display_symbol_selection_rich(filtered_results)
        else:
            selected_results = await self._display_symbol_selection_basic(filtered_results)
        
        if not selected_results:
            if RICH_AVAILABLE:
                self.console.print("❌ No symbols selected", style="yellow")
            else:
                print("❌ No symbols selected")
            return
        
        # Update status with selected symbols
        self.status.current_symbols = [result.symbol for result in selected_results]
        
        if RICH_AVAILABLE:
            self.console.print(f"✅ Selected symbols: {', '.join(self.status.current_symbols)}", style="green")
        else:
            print(f"✅ Selected symbols: {', '.join(self.status.current_symbols)}")
        
        # Check contracts and database status
        await self._check_contracts_and_data(selected_results)
    
    async def _search_symbols(self, search_term: str, instrument_type, exchange: str):
        """Search for symbols using Rithmic API"""
        return await self.rithmic_client.search_symbols(
            search_term,
            instrument_type=instrument_type,
            exchange=exchange
        )
    
    async def _display_symbol_selection_rich(self, results):
        """Display symbol selection using Rich interface"""
        if not RICH_AVAILABLE:
            return []
        
        # Create a table for display
        table = Table(title=f"Found {len(results)} Symbols", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Symbol", style="green")
        table.add_column("Product", style="blue")
        table.add_column("Month", style="yellow")
        table.add_column("Expiration", style="white")
        table.add_column("Name", style="dim")
        
        # Prepare display data
        display_items = []
        for i, result in enumerate(results, 1):
            # Extract month information
            month_code = ""
            month_name = ""
            symbol = result.symbol
            if len(symbol) > 2:
                for char in symbol[2:]:
                    if char.isalpha():
                        month_map = {
                            'H': 'March', 'M': 'June', 'U': 'September', 'Z': 'December'
                        }
                        if char.upper() in month_map:
                            month_code = char.upper()
                            month_name = month_map[month_code]
                        else:
                            month_code = char.upper()
                            month_name = month_code
                        break
            
            table.add_row(
                str(i),
                symbol,
                result.product_code,
                f"{month_code} ({month_name})" if month_name else month_code,
                str(result.expiration_date) if hasattr(result, 'expiration_date') else "N/A",
                result.symbol_name[:30] + "..." if len(result.symbol_name) > 30 else result.symbol_name
            )
            
            display_items.append({
                'index': i,
                'result': result,
                'month_code': month_code,
                'month_name': month_name
            })
        
        self.console.print(table)
        
        # Get user selection
        self.console.print("\n[bold yellow]Selection Options:[/bold yellow]")
        self.console.print("• Enter numbers separated by commas (e.g., 1,3,5)")
        self.console.print("• Enter 'all' to select all symbols")
        self.console.print("• Enter 'none' or press Enter to select none")
        
        selection = Prompt.ask("[cyan]Select symbols[/cyan]", default="none")
        
        if selection.lower() in ['none', '']:
            return []
        elif selection.lower() == 'all':
            return [item['result'] for item in display_items]
        else:
            try:
                # Parse comma-separated numbers
                indices = [int(x.strip()) for x in selection.split(',') if x.strip().isdigit()]
                selected_results = []
                
                for idx in indices:
                    if 1 <= idx <= len(display_items):
                        selected_results.append(display_items[idx-1]['result'])
                    else:
                        self.console.print(f"⚠️  Invalid selection: {idx}", style="yellow")
                
                return selected_results
                
            except ValueError:
                self.console.print("❌ Invalid selection format", style="red")
                return []
    
    async def _display_symbol_selection_basic(self, results):
        """Display symbol selection using basic interface"""
        print(f"\nFound {len(results)} symbols:")
        
        for i, result in enumerate(results, 1):
            # Extract month information
            month_code = ""
            month_name = ""
            symbol = result.symbol
            if len(symbol) > 2:
                for char in symbol[2:]:
                    if char.isalpha():
                        month_map = {
                            'H': 'March', 'M': 'June', 'U': 'September', 'Z': 'December'
                        }
                        if char.upper() in month_map:
                            month_code = char.upper()
                            month_name = month_map[month_code]
                        else:
                            month_code = char.upper()
                            month_name = month_code
                        break
            
            month_display = f" (Month: {month_name})" if month_name else ""
            print(f"{i}. Symbol: {symbol}{month_display} | Product: {result.product_code} | Exp: {result.expiration_date}")
        
        print("\nSelection options:")
        print("• Enter numbers separated by commas (e.g., 1,3,5)")
        print("• Enter 'all' to select all symbols")
        print("• Enter 'none' or press Enter to select none")
        
        selection = input("Select symbols: ") or "none"
        
        if selection.lower() in ['none', '']:
            return []
        elif selection.lower() == 'all':
            return results
        else:
            try:
                indices = [int(x.strip()) for x in selection.split(',') if x.strip().isdigit()]
                selected_results = []
                
                for idx in indices:
                    if 1 <= idx <= len(results):
                        selected_results.append(results[idx-1])
                    else:
                        print(f"⚠️  Invalid selection: {idx}")
                
                return selected_results
                
            except ValueError:
                print("❌ Invalid selection format")
                return []
    
    async def _check_contracts_and_data(self, selected_results):
        """Check contracts and existing data for selected symbols"""
        if RICH_AVAILABLE:
            with self.console.status("[bold blue]Checking contracts and data...") as status:
                await self._perform_contract_check(selected_results, status)
        else:
            print("Checking contracts and data...")
            await self._perform_contract_check(selected_results)
    
    async def _perform_contract_check(self, selected_results, status=None):
        """Perform the actual contract and data checking"""
        self.status.available_contracts = {}
        
        for result in selected_results:
            symbol = result.symbol
            product_code = result.product_code
            
            if status and RICH_AVAILABLE:
                status.update(f"[bold blue]Checking contracts for {symbol}...")
            elif not RICH_AVAILABLE:
                print(f"Checking contracts for {symbol}...")
            
            try:
                # Get front month contract
                front_month = await self._get_front_month_contract(product_code, self.status.current_exchange)
                
                # Store the contract
                self.status.available_contracts[symbol] = [symbol]  # Use the selected symbol as the contract
                
                # Display contract info
                if RICH_AVAILABLE:
                    self.console.print(f"📄 {symbol}: Contract found", style="green")
                else:
                    print(f"📄 {symbol}: Contract found")
                
                # Check database data if connected
                if self.status.db_connected:
                    try:
                        async with get_async_session() as session:
                            helper = TimescaleDBHelper(session)
                            
                            # Check data counts
                            from sqlalchemy import text
                            result_seconds = await session.execute(
                                text("SELECT COUNT(*) FROM market_data_seconds WHERE symbol = :symbol AND exchange = :exchange"),
                                {'symbol': symbol, 'exchange': self.status.current_exchange}
                            )
                            second_count = result_seconds.scalar()
                            
                            result_minutes = await session.execute(
                                text("SELECT COUNT(*) FROM market_data_minutes WHERE symbol = :symbol AND exchange = :exchange"),
                                {'symbol': symbol, 'exchange': self.status.current_exchange}
                            )
                            minute_count = result_minutes.scalar()
                            
                            total_datapoints = second_count + minute_count
                            
                            if RICH_AVAILABLE:
                                self.console.print(f"  💾 Data in TimescaleDB: {total_datapoints:,} total", style="blue")
                                self.console.print(f"    - Second bars: {second_count:,}", style="dim")
                                self.console.print(f"    - Minute bars: {minute_count:,}", style="dim")
                            else:
                                print(f"  💾 Data in TimescaleDB: {total_datapoints:,} total")
                                print(f"    - Second bars: {second_count:,}")
                                print(f"    - Minute bars: {minute_count:,}")
                            
                            # Get latest data timestamp
                            if total_datapoints > 0:
                                latest_result = await session.execute(
                                    text("""
                                        SELECT MAX(timestamp) FROM (
                                            SELECT timestamp FROM market_data_seconds WHERE symbol = :symbol AND exchange = :exchange
                                            UNION ALL
                                            SELECT timestamp FROM market_data_minutes WHERE symbol = :symbol AND exchange = :exchange
                                        ) combined
                                    """),
                                    {'symbol': symbol, 'exchange': self.status.current_exchange}
                                )
                                latest_timestamp = latest_result.scalar()
                                if latest_timestamp:
                                    if RICH_AVAILABLE:
                                        self.console.print(f"    - Latest data: {latest_timestamp}", style="dim")
                                    else:
                                        print(f"    - Latest data: {latest_timestamp}")
                            
                    except Exception as e:
                        if RICH_AVAILABLE:
                            self.console.print(f"  ⚠️  Error checking database data: {e}", style="yellow")
                        else:
                            print(f"  ⚠️  Error checking database data: {e}")
                else:
                    if RICH_AVAILABLE:
                        self.console.print("  ⚠️  TimescaleDB not connected - cannot check data", style="yellow")
                    else:
                        print("  ⚠️  TimescaleDB not connected - cannot check data")
                
            except Exception as e:
                if RICH_AVAILABLE:
                    self.console.print(f"❌ Error checking {symbol}: {e}", style="red")
                else:
                    print(f"❌ Error checking {symbol}: {e}")
        
        if RICH_AVAILABLE:
            self.console.print("✅ Symbol search and contract check completed", style="green")
        else:
            print("✅ Symbol search and contract check completed")
    
    async def _get_front_month_contract(self, symbol: str, exchange: str):
        """Get front month contract for a symbol"""
        try:
            results = await self._search_symbols(symbol, InstrumentType.FUTURE, exchange)
            filtered_contracts = [r for r in results if hasattr(r, 'product_code') and r.product_code.startswith(symbol)]
            
            if filtered_contracts:
                sorted_contracts = sorted(filtered_contracts, key=lambda x: x.expiration_date if hasattr(x, 'expiration_date') else x.symbol)
                return sorted_contracts[0].symbol if sorted_contracts else None
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting front month contract for {symbol}: {e}")
            return None

    async def download_historical_data_with_progress(self, days: int = 7):
        """Download historical data with enhanced progress tracking"""
        if not self.status.rithmic_connected or not self.status.db_connected:
            if RICH_AVAILABLE:
                self.console.print("❌ Both Rithmic and Database connections required", style="red")
            return
            
        if not self.status.available_contracts:
            if RICH_AVAILABLE:
                self.console.print("❌ No contracts available. Search symbols first.", style="red")
            return
        
        # Ask for data types
        if RICH_AVAILABLE:
            choice = Prompt.ask(
                "Select data types",
                choices=["1", "2", "3"],
                default="1",
                show_choices=False
            )
        else:
            print("1. Second bars")
            print("2. Minute bars") 
            print("3. Both")
            choice = input("Enter choice (default: 1): ") or "1"
        
        download_second_bars = choice in ['1', '3']
        download_minute_bars = choice in ['2', '3']
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Initialize progress tracking
        self.status.download_progress = {}
        total_contracts = sum(len(contracts) for contracts in self.status.available_contracts.values())
        
        if RICH_AVAILABLE:
            # Create progress display with Rich
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                
                main_task = progress.add_task("Overall Progress", total=total_contracts)
                
                try:
                    async with get_async_session() as session:
                        helper = TimescaleDBHelper(session)
                        
                        for symbol, contracts in self.status.available_contracts.items():
                            for contract in contracts:
                                
                                if download_second_bars:
                                    await self._download_with_progress(
                                        helper, contract, symbol, start_time, end_time,
                                        "second", TimeBarType.SECOND_BAR, 1, progress, main_task
                                    )
                                
                                if download_minute_bars:
                                    await self._download_with_progress(
                                        helper, contract, symbol, start_time, end_time,
                                        "minute", TimeBarType.MINUTE_BAR, 1, progress, main_task
                                    )
                                
                                progress.advance(main_task)
                                
                except Exception as e:
                    self.console.print(f"❌ Download failed: {e}", style="red")
                    logger.exception("Download failed")
        else:
            # Fallback without Rich
            print(f"Downloading {days} days of data...")
            # Implement basic download without progress bars
            
        # Verify data was inserted
        await self._verify_data_insertion()

    async def _download_with_progress(self, helper: TimescaleDBHelper, contract: str, symbol: str, 
                                     start_time: datetime, end_time: datetime, data_type: str,
                                     bar_type: TimeBarType, interval: int, progress: Progress, main_task: TaskID):
        """Download data with detailed progress tracking and live updates"""
        
        progress_key = f"{contract}_{data_type}"
        
        # Estimate chunks based on time range and data type
        time_diff = end_time - start_time
        if data_type == "second":
            max_chunk_hours = 6
            estimated_chunks = max(1, int(time_diff.total_seconds() / (max_chunk_hours * 3600)))
        else:
            max_chunk_days = 2  
            estimated_chunks = max(1, int(time_diff.days / max_chunk_days))
        
        # Initialize progress tracking
        self.status.download_progress[progress_key] = DownloadProgress(
            contract=contract,
            data_type=data_type,
            total_chunks=estimated_chunks,
            completed_chunks=0,
            current_chunk_info="🚀 Starting download...",
            total_records=0,
            start_time=datetime.now()
        )
        
        # Update live display
        self.update_live_display()
        
        task = progress.add_task(f"{contract} {data_type}", total=estimated_chunks)
        
        try:
            all_bars = []
            current_start = start_time
            completed_chunks = 0
            
            if data_type == "second":
                max_chunk_hours = 6
                chunk_interval = timedelta(hours=max_chunk_hours)
            else:
                max_chunk_days = 2
                chunk_interval = timedelta(days=max_chunk_days)
            
            while current_start < end_time:
                current_end = min(end_time, current_start + chunk_interval)
                
                # Update progress with current chunk info
                chunk_info = f"📥 {current_start.strftime('%m/%d %H:%M')}-{current_end.strftime('%H:%M')}"
                self.update_progress_display(
                    contract, data_type, chunk_info, 
                    completed_chunks, estimated_chunks, len(all_bars)
                )
                
                progress.update(task, description=f"{contract} {data_type} - {chunk_info}")
                
                try:
                    chunk_bars = await self.rithmic_client.get_historical_time_bars(
                        contract,
                        self.status.current_exchange,
                        current_start,
                        current_end,
                        bar_type,
                        interval
                    )
                    
                    if chunk_bars:
                        all_bars.extend(chunk_bars)
                        # Update progress with new record count
                        self.update_progress_display(
                            contract, data_type, f"✅ +{len(chunk_bars)} bars", 
                            completed_chunks + 1, estimated_chunks, len(all_bars)
                        )
                    else:
                        # Update progress showing empty chunk
                        self.update_progress_display(
                            contract, data_type, "⚠️ No data in chunk", 
                            completed_chunks + 1, estimated_chunks, len(all_bars)
                        )
                    
                    completed_chunks += 1
                    progress.advance(task)
                    
                    # If we hit API limit, reduce chunk size
                    if len(chunk_bars) >= 9999:
                        if data_type == "second" and max_chunk_hours > 1:
                            max_chunk_hours = max_chunk_hours / 2
                            chunk_interval = timedelta(hours=max_chunk_hours)
                            self.update_progress_display(
                                contract, data_type, f"⚙️ Reduced chunk size to {max_chunk_hours}h", 
                                completed_chunks, estimated_chunks, len(all_bars)
                            )
                        elif data_type == "minute" and max_chunk_days > 0.5:
                            max_chunk_days = max_chunk_days / 2
                            chunk_interval = timedelta(days=max_chunk_days)
                            self.update_progress_display(
                                contract, data_type, f"⚙️ Reduced chunk size to {max_chunk_days}d", 
                                completed_chunks, estimated_chunks, len(all_bars)
                            )
                    
                except Exception as e:
                    logger.error(f"Error fetching chunk for {contract}: {e}")
                    self.update_progress_display(
                        contract, data_type, f"❌ Error: {str(e)[:20]}...", 
                        completed_chunks + 1, estimated_chunks, len(all_bars)
                    )
                    progress.advance(task)
                    completed_chunks += 1
                
                current_start = current_end
                
                # Small delay to show progress updates
                await asyncio.sleep(0.1)
            
            # Save to database if we have data
            if all_bars:
                self.update_progress_display(
                    contract, data_type, "💾 Saving to database...", 
                    completed_chunks, estimated_chunks, len(all_bars)
                )
                progress.update(task, description=f"{contract} {data_type} - Saving to DB...")
                
                data_records = []
                for bar in all_bars:
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
                        'volume': bar.get('volume', 0),
                        'tick_count': bar.get('tick_count', 1),
                        'vwap': float(bar.get('vwap', bar.get('close', 0))),
                        'bid': None,
                        'ask': None,
                        'spread': None,
                        'data_quality_score': 1.0,
                        'is_regular_hours': True
                    }
                    data_records.append(record)
                
                table_name = 'market_data_seconds' if data_type == 'second' else 'market_data_minutes'
                await helper.bulk_insert_market_data(data_records, table_name)
                
                # Final update
                self.update_progress_display(
                    contract, data_type, f"✅ Saved {len(data_records):,} records", 
                    completed_chunks, estimated_chunks, len(all_bars)
                )
            else:
                # No data to save
                self.update_progress_display(
                    contract, data_type, "⚠️ No data received", 
                    completed_chunks, estimated_chunks, 0
                )
                
        except Exception as e:
            logger.error(f"Error downloading {data_type} bars for {contract}: {e}")
            self.update_progress_display(
                contract, data_type, f"❌ Failed: {str(e)[:30]}...", 
                completed_chunks, estimated_chunks, len(all_bars) if 'all_bars' in locals() else 0
            )

    async def _verify_data_insertion(self):
        """Verify data was actually inserted into the database"""
        try:
            async with get_async_session() as session:
                from sqlalchemy import text
                
                # Check second data
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
                second_count = result.scalar()
                
                # Check minute data
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
                minute_count = result.scalar()
                
                if RICH_AVAILABLE:
                    table = Table(title="Database Verification")
                    table.add_column("Table", style="cyan")
                    table.add_column("Record Count", style="green")
                    
                    table.add_row("market_data_seconds", f"{second_count:,}")
                    table.add_row("market_data_minutes", f"{minute_count:,}")
                    
                    self.console.print(table)
                    
                    if second_count == 0 and minute_count == 0:
                        self.console.print("⚠️  No data found in database! Check logs for errors.", style="yellow")
                else:
                    print(f"Database verification:")
                    print(f"Second data: {second_count:,} records")
                    print(f"Minute data: {minute_count:,} records")
                    
        except Exception as e:
            logger.error(f"Error verifying data insertion: {e}")
            if RICH_AVAILABLE:
                self.console.print(f"❌ Error verifying data: {e}", style="red")

    async def run(self):
        """Main application loop"""
        try:
            while True:
                self.display_main_menu()
                
                if RICH_AVAILABLE:
                    choice = Prompt.ask("Enter your choice", choices=["0", "1", "2", "3", "4", "5"])
                else:
                    choice = input("\nEnter your choice: ")
                
                if choice == '1':
                    await self.test_connections()
                    if not RICH_AVAILABLE:
                        input("\nPress Enter to continue...")
                elif choice == '2':
                    await self.search_symbols_and_contracts()
                    if not RICH_AVAILABLE:
                        input("\nPress Enter to continue...")
                elif choice == '3':
                    if RICH_AVAILABLE:
                        days = int(Prompt.ask("Enter number of days to download", default="7"))
                    else:
                        days = int(input("Enter number of days to download (default: 7): ") or "7")
                    await self.download_historical_data_with_progress(days)
    async def view_database_data(self):
        """View TimescaleDB data with Rich formatting"""
        if not self.status.db_connected:
            if RICH_AVAILABLE:
                self.console.print("❌ Not connected to TimescaleDB. Please test connections first.", style="red")
            else:
                print("❌ Not connected to TimescaleDB. Please test connections first.")
            return
        
        if RICH_AVAILABLE:
            with self.console.status("[bold blue]Loading database information...") as status:
                await self._display_database_info()
        else:
            print("Loading database information...")
            await self._display_database_info()
    
    async def _display_database_info(self):
        """Display comprehensive database information"""
        try:
            async with get_async_session() as session:
                from sqlalchemy import text
                
                # Table Summary
                if RICH_AVAILABLE:
                    self.console.print("\n[bold cyan]📊 Table Summary[/bold cyan]")
                else:
                    print("\n📊 Table Summary")
                
                table_counts = {}
                tables = ['market_data_seconds', 'market_data_minutes', 'raw_tick_data', 'predictions', 'trades']
                
                for table in tables:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        table_counts[table] = count
                    except Exception as e:
                        table_counts[table] = f"Error: {e}"
                
                if RICH_AVAILABLE:
                    summary_table = Table(title="Database Tables")
                    summary_table.add_column("Table", style="cyan")
                    summary_table.add_column("Record Count", style="green")
                    
                    for table, count in table_counts.items():
                        count_str = f"{count:,}" if isinstance(count, int) else str(count)
                        style = "green" if isinstance(count, int) and count > 0 else "yellow" if isinstance(count, int) else "red"
                        summary_table.add_row(table, count_str)
                    
                    self.console.print(summary_table)
                else:
                    for table, count in table_counts.items():
                        count_str = f"{count:,}" if isinstance(count, int) else str(count)
                        print(f"{table}: {count_str}")
                
                # Available Symbols
                if RICH_AVAILABLE:
                    self.console.print("\n[bold cyan]📈 Available Symbols[/bold cyan]")
                else:
                    print("\n📈 Available Symbols")
                
                result = await session.execute(text("""
                    SELECT symbol, exchange, COUNT(*) as count,
                           MIN(timestamp) as first_data,
                           MAX(timestamp) as last_data
                    FROM market_data_seconds
                    GROUP BY symbol, exchange
                    ORDER BY count DESC, symbol, exchange
                """))
                symbols_data = result.fetchall()
                
                if symbols_data:
                    if RICH_AVAILABLE:
                        symbols_table = Table(title="Symbol Data Summary")
                        symbols_table.add_column("Symbol", style="cyan")
                        symbols_table.add_column("Exchange", style="blue")
                        symbols_table.add_column("Records", style="green")
                        symbols_table.add_column("First Data", style="yellow")
                        symbols_table.add_column("Last Data", style="yellow")
                        
                        for row in symbols_data:
                            symbols_table.add_row(
                                row[0],  # symbol
                                row[1],  # exchange
                                f"{row[2]:,}",  # count
                                str(row[3])[:19] if row[3] else "N/A",  # first_data
                                str(row[4])[:19] if row[4] else "N/A"   # last_data
                            )
                        
                        self.console.print(symbols_table)
                    else:
                        for row in symbols_data:
                            print(f"{row[0]} ({row[1]}): {row[2]:,} records, {row[3]} to {row[4]}")
                else:
                    if RICH_AVAILABLE:
                        self.console.print("No data found in market_data_seconds table", style="yellow")
                    else:
                        print("No data found in market_data_seconds table")
                
                # Recent Data Sample
                if table_counts.get('market_data_seconds', 0) > 0:
                    if RICH_AVAILABLE:
                        self.console.print("\n[bold cyan]📋 Recent Data Sample[/bold cyan]")
                    else:
                        print("\n📋 Recent Data Sample")
                    
                    result = await session.execute(text("""
                        SELECT timestamp, symbol, contract, exchange,
                               open, high, low, close, volume
                        FROM market_data_seconds
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """))
                    recent_data = result.fetchall()
                    
                    if RICH_AVAILABLE:
                        recent_table = Table(title="Recent Market Data")
                        recent_table.add_column("Time", style="yellow")
                        recent_table.add_column("Symbol", style="cyan")
                        recent_table.add_column("Contract", style="blue")
                        recent_table.add_column("OHLC", style="green")
                        recent_table.add_column("Volume", style="red")
                        
                        for row in recent_data:
                            timestamp_str = str(row[0])[:19] if row[0] else "N/A"
                            ohlc_str = f"O:{row[4]:.2f} H:{row[5]:.2f} L:{row[6]:.2f} C:{row[7]:.2f}"
                            recent_table.add_row(
                                timestamp_str,
                                row[1],  # symbol
                                row[2],  # contract
                                ohlc_str,
                                f"{row[8]:,}" if row[8] else "0"  # volume
                            )
                        
                        self.console.print(recent_table)
                    else:
                        for row in recent_data:
                            print(f"{row[0]} | {row[1]} {row[2]} | O:{row[4]} H:{row[5]} L:{row[6]} C:{row[7]} V:{row[8]}")
                
                # Hypertable Information
                if RICH_AVAILABLE:
                    self.console.print("\n[bold cyan]⏰ Hypertable Information[/bold cyan]")
                else:
                    print("\n⏰ Hypertable Information")
                
                try:
                    result = await session.execute(text("""
                        SELECT hypertable_name, num_chunks, num_dimensions,
                               table_bytes, index_bytes, toast_bytes, total_bytes
                        FROM timescaledb_information.hypertables h
                        LEFT JOIN timescaledb_information.hypertable_detailed_size(h.hypertable_name) s ON true
                        ORDER BY hypertable_name;
                    """))
                    hypertables = result.fetchall()
                    
                    if hypertables:
                        if RICH_AVAILABLE:
                            ht_table = Table(title="Hypertables Status")
                            ht_table.add_column("Table", style="cyan")
                            ht_table.add_column("Chunks", style="green")
                            ht_table.add_column("Dimensions", style="blue")
                            ht_table.add_column("Size", style="yellow")
                            
                            for ht in hypertables:
                                size_mb = ht[6] / (1024*1024) if ht[6] else 0
                                size_str = f"{size_mb:.1f} MB" if size_mb > 0 else "N/A"
                                ht_table.add_row(
                                    ht[0],  # hypertable_name
                                    str(ht[1]) if ht[1] else "0",  # num_chunks
                                    str(ht[2]) if ht[2] else "0",  # num_dimensions
                                    size_str
                                )
                            
                            self.console.print(ht_table)
                        else:
                            for ht in hypertables:
                                size_mb = ht[6] / (1024*1024) if ht[6] else 0
                                print(f"{ht[0]}: {ht[1]} chunks, {ht[2]} dimensions, {size_mb:.1f} MB")
                    else:
                        if RICH_AVAILABLE:
                            self.console.print("No hypertables found", style="yellow")
                        else:
                            print("No hypertables found")
                            
                except Exception as e:
                    if RICH_AVAILABLE:
                        self.console.print(f"⚠️  Could not get hypertable info: {e}", style="yellow")
                    else:
                        print(f"⚠️  Could not get hypertable info: {e}")
                
                # Data Quality Check
                if table_counts.get('market_data_seconds', 0) > 0:
                    if RICH_AVAILABLE:
                        self.console.print("\n[bold cyan]🔍 Data Quality Check[/bold cyan]")
                    else:
                        print("\n🔍 Data Quality Check")
                    
                    # Check for potential issues
                    quality_checks = []
                    
                    # Check for records with zero volume
                    result = await session.execute(text("""
                        SELECT COUNT(*) FROM market_data_seconds WHERE volume = 0 OR volume IS NULL
                    """))
                    zero_volume = result.scalar()
                    if zero_volume > 0:
                        quality_checks.append(f"Records with zero/null volume: {zero_volume:,}")
                    
                    # Check for invalid OHLC
                    result = await session.execute(text("""
                        SELECT COUNT(*) FROM market_data_seconds 
                        WHERE high < low OR high < open OR high < close OR low > open OR low > close
                    """))
                    invalid_ohlc = result.scalar()
                    if invalid_ohlc > 0:
                        quality_checks.append(f"Records with invalid OHLC: {invalid_ohlc:,}")
                    
                    # Check for extreme price movements (>50% in one bar)
                    result = await session.execute(text("""
                        SELECT COUNT(*) FROM market_data_seconds 
                        WHERE ABS(high - low) / ((high + low) / 2) > 0.5
                    """))
                    extreme_moves = result.scalar()
                    if extreme_moves > 0:
                        quality_checks.append(f"Records with extreme price moves (>50%): {extreme_moves:,}")
                    
                    if quality_checks:
                        if RICH_AVAILABLE:
                            for check in quality_checks:
                                self.console.print(f"⚠️  {check}", style="yellow")
                        else:
                            for check in quality_checks:
                                print(f"⚠️  {check}")
                    else:
                        if RICH_AVAILABLE:
                            self.console.print("✅ No obvious data quality issues found", style="green")
                        else:
                            print("✅ No obvious data quality issues found")
                
        except Exception as e:
            if RICH_AVAILABLE:
                self.console.print(f"❌ Error viewing database data: {e}", style="red")
            else:
                print(f"❌ Error viewing database data: {e}")

                elif choice == '4':
                    await self.view_database_data()
                    if not RICH_AVAILABLE:
                        input("\nPress Enter to continue...")
    async def initialize_database_setup(self):
        """Initialize database with Rich progress display"""
        if RICH_AVAILABLE:
            self.console.print("[bold yellow]🔧 Initialize TimescaleDB[/bold yellow]")
            
            # Confirm with user
            confirm = Confirm.ask("This will set up database tables and extensions. Continue?")
            if not confirm:
                self.console.print("❌ Database initialization cancelled", style="yellow")
                return
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                
                # Task 1: Test connection
                task1 = progress.add_task("Testing database connection...", total=1)
                try:
                    db_manager = get_database_manager()
                    connection_ok = await db_manager.test_connection()
                    
                    if not connection_ok:
                        self.console.print("❌ Database connection failed", style="red")
                        return
                    
                    progress.update(task1, completed=1)
                    self.console.print("✅ Database connection successful", style="green")
                except Exception as e:
                    self.console.print(f"❌ Connection test failed: {e}", style="red")
                    return
                
                # Task 2: Initialize extensions
                task2 = progress.add_task("Initializing database extensions...", total=1)
                try:
                    await db_manager.initialize_database()
                    progress.update(task2, completed=1)
                    self.console.print("✅ Database extensions initialized", style="green")
                except Exception as e:
                    self.console.print(f"❌ Extension initialization failed: {e}", style="red")
                    return
                
                # Task 3: Create/verify tables
                task3 = progress.add_task("Creating and verifying tables...", total=1)
                try:
                    tables_ok = await db_manager.verify_tables()
                    if not tables_ok:
                        # Try to create tables using the setup script
                        from shared.database.connection import test_database_setup
                        await test_database_setup()
                    
                    progress.update(task3, completed=1)
                    self.console.print("✅ Tables created and verified", style="green")
                except Exception as e:
                    self.console.print(f"❌ Table creation failed: {e}", style="red")
                    return
                
                # Task 4: Verify hypertables
                task4 = progress.add_task("Setting up hypertables...", total=1)
                try:
                    hypertables_ok = await db_manager.verify_hypertables()
                    progress.update(task4, completed=1)
                    
                    if hypertables_ok:
                        self.console.print("✅ Hypertables configured", style="green")
                    else:
                        self.console.print("⚠️  No hypertables found - using regular tables", style="yellow")
                except Exception as e:
                    self.console.print(f"⚠️  Hypertable setup issue: {e}", style="yellow")
                
                # Task 5: Test data insertion
                task5 = progress.add_task("Testing data insertion...", total=1)
                try:
                    async with get_async_session() as session:
                        helper = TimescaleDBHelper(session)
                        
                        # Test insertion
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
                        
                    progress.update(task5, completed=1)
                    self.console.print("✅ Data insertion test successful", style="green")
                    
                except Exception as e:
                    self.console.print(f"❌ Data insertion test failed: {e}", style="red")
                    return
            
            # Update connection status
            self.status.db_connected = True
            self.console.print("\n🎉 Database initialization completed successfully!", style="bold green")
            
        else:
            # Fallback for basic interface
            print("🔧 Initialize TimescaleDB")
            confirm = input("This will set up database tables and extensions. Continue? (y/n): ")
            if confirm.lower() != 'y':
                print("❌ Database initialization cancelled")
                return
            
            print("1. Testing connection...")
            try:
                db_manager = get_database_manager()
                connection_ok = await db_manager.test_connection()
                if not connection_ok:
                    print("❌ Database connection failed")
                    return
                print("✅ Connection successful")
                
                print("2. Initializing extensions...")
                await db_manager.initialize_database()
                print("✅ Extensions initialized")
                
                print("3. Creating tables...")
                from shared.database.connection import test_database_setup
                await test_database_setup()
                print("✅ Tables created")
                
                self.status.db_connected = True
                print("🎉 Database initialization completed!")
                
            except Exception as e:
                print(f"❌ Initialization failed: {e}")

                elif choice == '5':
                    await self.initialize_database_setup()
                    if not RICH_AVAILABLE:
                        input("\nPress Enter to continue...")
                elif choice == '0':
                    if self.rithmic_client and self.status.rithmic_connected:
                        if RICH_AVAILABLE:
                            self.console.print("Disconnecting from Rithmic...", style="yellow")
                        await self.disconnect_from_rithmic()
                    break
                else:
                    if RICH_AVAILABLE:
                        self.console.print("Invalid choice. Please try again.", style="red")
                    else:
                        print("Invalid choice. Please try again.")
                
                if RICH_AVAILABLE:
                    input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                self.console.print("\n👋 Goodbye!", style="yellow")
            else:
                print("\nProgram terminated by user")
        except Exception as e:
            logger.exception("Unhandled exception in main loop")
            if RICH_AVAILABLE:
                self.console.print(f"❌ Unhandled exception: {e}", style="red")
            else:
                print(f"Unhandled exception: {e}")

    async def test_connections(self):
        """Test database and Rithmic connections with live updates"""
        if RICH_AVAILABLE:
            # Create a temporary status for connection testing
            with self.console.status("[bold green]Testing connections...") as status:
                # Test database
                status.update("[bold blue]Testing TimescaleDB connection...")
                try:
                    db_manager = get_database_manager()
                    connection_ok = await db_manager.test_connection()
                    if connection_ok:
                        self.console.print("✅ TimescaleDB connection successful", style="green")
                        self.status.db_connected = True
                        
                        # Verify tables exist
                        async with get_async_session() as session:
                            from sqlalchemy import text
                            result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds LIMIT 1"))
                            self.console.print("✅ TimescaleDB tables accessible", style="green")
                    else:
                        self.console.print("❌ TimescaleDB connection failed", style="red")
                        self.status.db_connected = False
                except Exception as e:
                    self.console.print(f"❌ TimescaleDB connection error: {e}", style="red")
                    self.status.db_connected = False
                
                # Test Rithmic
                status.update("[bold blue]Testing Rithmic connection...")
                await self.connect_to_rithmic()
                
                # Update the live display with new connection status
                if hasattr(self, '_live_display') and self._live_display:
                    await asyncio.sleep(0.5)  # Brief pause to show results
                    self._live_display.update(self._create_main_layout())
        else:
            print("Testing connections...")
            await self.connect_to_rithmic()

    async def download_historical_data_with_progress(self, days: int = 7):
        """Download historical data with enhanced progress tracking and live updates"""
        if not self.status.rithmic_connected or not self.status.db_connected:
            if RICH_AVAILABLE:
                self.console.print("❌ Both Rithmic and Database connections required", style="red")
            return
            
        if not self.status.available_contracts:
            if RICH_AVAILABLE:
                self.console.print("❌ No contracts available. Search symbols first.", style="red")
            return
        
        # Ask for data types
        if RICH_AVAILABLE:
            choice = Prompt.ask(
                "Select data types",
                choices=["1", "2", "3"],
                default="1",
                show_choices=True
            )
        else:
            print("1. Second bars")
            print("2. Minute bars") 
            print("3. Both")
            choice = input("Enter choice (default: 1): ") or "1"
        
        download_second_bars = choice in ['1', '3']
        download_minute_bars = choice in ['2', '3']
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Initialize progress tracking
        self.status.download_progress = {}
        total_downloads = 0
        
        # Count total downloads needed
        for symbol, contracts in self.status.available_contracts.items():
            for contract in contracts:
                if download_second_bars:
                    total_downloads += 1
                if download_minute_bars:
                    total_downloads += 1
        
        if RICH_AVAILABLE:
            self.console.print(f"\n[bold yellow]📥 Starting download of {days} days of data[/bold yellow]")
            self.console.print(f"Data types: {'Second bars' if download_second_bars else ''}{',' if download_second_bars and download_minute_bars else ''}{'Minute bars' if download_minute_bars else ''}")
            self.console.print(f"Total downloads: {total_downloads}")
            
            # Create progress display with Rich
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                
                main_task = progress.add_task("Overall Progress", total=total_downloads)
                downloads_completed = 0
                
                try:
                    async with get_async_session() as session:
                        helper = TimescaleDBHelper(session)
                        
                        for symbol, contracts in self.status.available_contracts.items():
                            for contract in contracts:
                                
                                if download_second_bars:
                                    await self._download_with_progress(
                                        helper, contract, symbol, start_time, end_time,
                                        "second", TimeBarType.SECOND_BAR, 1, progress, main_task
                                    )
                                    downloads_completed += 1
                                    progress.update(main_task, completed=downloads_completed)
                                
                                if download_minute_bars:
                                    await self._download_with_progress(
                                        helper, contract, symbol, start_time, end_time,
                                        "minute", TimeBarType.MINUTE_BAR, 1, progress, main_task
                                    )
                                    downloads_completed += 1
                                    progress.update(main_task, completed=downloads_completed)
                                
                                # Update live display periodically
                                if hasattr(self, '_live_display') and self._live_display:
                                    self._live_display.update(self._create_main_layout())
                                
                except Exception as e:
                    self.console.print(f"❌ Download failed: {e}", style="red")
                    logger.exception("Download failed")
        else:
            # Fallback without Rich
            print(f"Downloading {days} days of data...")
            print("This may take several minutes...")
            
            try:
                async with get_async_session() as session:
                    helper = TimescaleDBHelper(session)
                    
                    for symbol, contracts in self.status.available_contracts.items():
                        for contract in contracts:
                            print(f"Processing {contract}...")
                            
                            if download_second_bars:
                                print(f"  Downloading second bars...")
                                # Simplified download without progress bars
                                await self._download_simple(helper, contract, symbol, start_time, end_time, "second")
                            
                            if download_minute_bars:
                                print(f"  Downloading minute bars...")
                                await self._download_simple(helper, contract, symbol, start_time, end_time, "minute")
            except Exception as e:
                print(f"❌ Download failed: {e}")
                logger.exception("Download failed")
        
        # Verify data was inserted
        await self._verify_data_insertion()

    async def _download_simple(self, helper: TimescaleDBHelper, contract: str, symbol: str,
                              start_time: datetime, end_time: datetime, data_type: str):
        """Simple download without progress bars for fallback mode"""
        try:
            if data_type == "second":
                bar_type = TimeBarType.SECOND_BAR
                interval = 1
                table_name = 'market_data_seconds'
            else:
                bar_type = TimeBarType.MINUTE_BAR
                interval = 1
                table_name = 'market_data_minutes'
            
            # Download data in chunks
            all_bars = []
            current_start = start_time
            chunk_interval = timedelta(hours=6 if data_type == "second" else 48)
            
            while current_start < end_time:
                current_end = min(end_time, current_start + chunk_interval)
                
                try:
                    chunk_bars = await self.rithmic_client.get_historical_time_bars(
                        contract,
                        self.status.current_exchange,
                        current_start,
                        current_end,
                        bar_type,
                        interval
                    )
                    
                    if chunk_bars:
                        all_bars.extend(chunk_bars)
                        print(f"    Downloaded {len(chunk_bars)} bars from {current_start.strftime('%m/%d %H:%M')}")
                    
                except Exception as e:
                    print(f"    Error downloading chunk: {e}")
                
                current_start = current_end
            
            # Save to database
            if all_bars:
                print(f"    Saving {len(all_bars)} bars to database...")
                data_records = []
                for bar in all_bars:
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
                        'volume': bar.get('volume', 0),
                        'tick_count': bar.get('tick_count', 1),
                        'vwap': float(bar.get('vwap', bar.get('close', 0))),
                        'bid': None,
                        'ask': None,
                        'spread': None,
                        'data_quality_score': 1.0,
                        'is_regular_hours': True
                    }
                    data_records.append(record)
                
                await helper.bulk_insert_market_data(data_records, table_name)
                print(f"    ✅ Saved {len(data_records)} records")
            else:
                print(f"    ⚠️ No data received")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            logger.exception(f"Error in simple download for {contract}")

async def main():
    """Main entry point with better error handling"""
    if not RICH_AVAILABLE:
        print("⚠️  For the best experience, install Rich: pip install rich")
        print("Running with basic interface...\n")
    
    app = RithmicAdminTUI()
    
    try:
        await app.run()
    except Exception as e:
        logger.exception("Fatal error in main application")
        if RICH_AVAILABLE:
            app.console.print(f"💥 Fatal error: {e}", style="bold red")
        else:
            print(f"💥 Fatal error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Program terminated by user")
    except Exception as e:
        print(f"💥 Unhandled exception: {e}")
        logging.exception("Unhandled exception in main")

    async def disconnect_from_rithmic(self, timeout=5.0):
        """Disconnect from Rithmic with timeout"""
        if self.rithmic_client and self.status.rithmic_connected:
            try:
                import sys
                from io import StringIO
                
                # Capture stderr to suppress disconnect warnings
                original_stderr = sys.stderr
                string_buffer = StringIO()
                
                try:
                    sys.stderr = string_buffer
                    await asyncio.wait_for(self.rithmic_client.disconnect(), timeout=timeout)
                finally:
                    sys.stderr = original_stderr
                    
                if RICH_AVAILABLE:
                    self.console.print("✅ Rithmic connection closed successfully", style="green")
                    
            except asyncio.TimeoutError:
                if RICH_AVAILABLE:
                    self.console.print("⚠️  Disconnect timed out (expected behavior)", style="yellow")
            except Exception as e:
                if RICH_AVAILABLE:
                    self.console.print(f"⚠️  Error during disconnect: {e}", style="yellow")
            finally:
                self.status.rithmic_connected = False

async def main():
    """Main entry point"""
    if not RICH_AVAILABLE:
        print("⚠️  For the best experience, install Rich: pip install rich")
        print("Running with basic interface...\n")
    
    app = RithmicAdminTUI()
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unhandled exception: {e}")
        logging.exception("Unhandled exception in main")