import os
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
        """Create progress panel showing download progress"""
        if not RICH_AVAILABLE or not self.status.download_progress:
            return None
            
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Contract", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Chunks", style="blue")
        table.add_column("Records", style="red")
        table.add_column("Current Chunk", style="white")
        
        for key, progress in self.status.download_progress.items():
            progress_bar = f"[{'█' * int(progress.progress_percent / 5)}{'░' * (20 - int(progress.progress_percent / 5))}]"
            progress_text = f"{progress_bar} {progress.progress_percent:.1f}%"
            
            table.add_row(
                progress.contract,
                progress.data_type.title(),
                progress_text,
                f"{progress.completed_chunks}/{progress.total_chunks}",
                f"{progress.total_records:,}",
                progress.current_chunk_info
            )
        
        return Panel(table, title="Download Progress", border_style="green")
    
    def display_main_menu(self):
        """Display the main menu"""
        if RICH_AVAILABLE:
            self.console.clear()
            
            # Create layout
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=8),
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
                    Layout(progress_panel, size=10),
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
            
            self.console.print(layout)
        else:
            # Fallback for no Rich
            print("\n" + "="*60)
            print("RITHMIC DATA ADMIN TOOL".center(60))
            print("="*60)
            print(f"Rithmic: {'Connected' if self.status.rithmic_connected else 'Disconnected'}")
            print(f"Database: {'Connected' if self.status.db_connected else 'Disconnected'}")
            print("-"*60)
            print("1. Test Connections (DB + Rithmic)")
            print("2. Search Symbols & Check Contracts")
            print("3. Download Historical Data")
            print("4. View TimescaleDB Data")
            print("5. Initialize/Setup Database")
            print("0. Exit")
            print("-"*60)

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
        """Download data with detailed progress tracking"""
        
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
            current_chunk_info="Starting...",
            total_records=0,
            start_time=datetime.now()
        )
        
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
                chunk_info = f"{current_start.strftime('%m/%d %H:%M')} to {current_end.strftime('%m/%d %H:%M')}"
                self.status.download_progress[progress_key].current_chunk_info = chunk_info
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
                        self.status.download_progress[progress_key].total_records += len(chunk_bars)
                    
                    completed_chunks += 1
                    self.status.download_progress[progress_key].completed_chunks = completed_chunks
                    progress.advance(task)
                    
                    # If we hit API limit, reduce chunk size
                    if len(chunk_bars) >= 9999:
                        if data_type == "second" and max_chunk_hours > 1:
                            max_chunk_hours = max_chunk_hours / 2
                            chunk_interval = timedelta(hours=max_chunk_hours)
                        elif data_type == "minute" and max_chunk_days > 0.5:
                            max_chunk_days = max_chunk_days / 2
                            chunk_interval = timedelta(days=max_chunk_days)
                    
                except Exception as e:
                    logger.error(f"Error fetching chunk for {contract}: {e}")
                    progress.advance(task)
                    completed_chunks += 1
                
                current_start = current_end
            
            # Save to database if we have data
            if all_bars:
                self.status.download_progress[progress_key].current_chunk_info = "Saving to database..."
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
                
                self.status.download_progress[progress_key].current_chunk_info = f"Saved {len(data_records):,} records"
                
        except Exception as e:
            logger.error(f"Error downloading {data_type} bars for {contract}: {e}")
            self.status.download_progress[progress_key].current_chunk_info = f"Error: {str(e)[:50]}..."

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
                    # Search symbols implementation
                    if RICH_AVAILABLE:
                        self.console.print("🔍 Symbol search not yet implemented in TUI version", style="yellow")
                    else:
                        print("Symbol search not yet implemented")
                elif choice == '3':
                    if RICH_AVAILABLE:
                        days = int(Prompt.ask("Enter number of days to download", default="7"))
                    else:
                        days = int(input("Enter number of days to download (default: 7): ") or "7")
                    await self.download_historical_data_with_progress(days)
                elif choice == '4':
                    # View database data
                    if RICH_AVAILABLE:
                        self.console.print("📊 Database viewer not yet implemented in TUI version", style="yellow")
                    else:
                        print("Database viewer not yet implemented")
                elif choice == '5':
                    # Initialize database
                    if RICH_AVAILABLE:
                        self.console.print("🔧 Database initialization not yet implemented in TUI version", style="yellow")
                    else:
                        print("Database initialization not yet implemented")
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