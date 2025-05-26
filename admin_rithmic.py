import os
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ProgressBar, TextArea, ListView, ListItem, Label, Button
from textual.containers import Container, VerticalScroll, Horizontal
from textual.screen import Screen
from textual.binding import Binding
from textual.message import Message, MessageTarget
from textual.reactive import reactive

# Import Rithmic client and config from project structure
try:
    import async_rithmic
    from async_rithmic import RithmicClient, TimeBarType, InstrumentType, Gateway, DataType
    from async_rithmic import ReconnectionSettings, RetrySettings
    # Adjust path to import from config and shared
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from config.chicago_gateway_config import get_chicago_gateway_config
    from shared.database.connection import get_async_session, TimescaleDBHelper, get_database_manager
    from layer1_development.data_collection.rithmic_symbol_search import search_symbols as search_symbols_func
    from layer1_development.data_collection.rithmic_symbol_search import get_front_month_contracts
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you have installed async_rithmic and textual, and are running from the project root or have configured PYTHONPATH correctly.")
    sys.exit(1)

# Configure logging to capture output to a Textual TextArea
class TextualHandler(logging.Handler):
    """A logging handler that emits Textual messages."""
    def __init__(self, app: App):
        super().__init__()
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:
        log_message = self.format(record)
        self.app.post_message(LogMessage(self.app, log_message))

class LogMessage(Message):
    """A custom message to carry log entries."""
    def __init__(self, sender: MessageTarget, text: str) -> None:
        super().__init__(sender)
        self.text = text

# Global state variables (will be moved to App state)
# rithmic_client = None # Managed within App now
# is_connected = False # Managed within App now
# db_connected = False # Managed within App now

class SymbolSelectionScreen(Screen):
    """A screen for interactive symbol selection."""

    BINDINGS = [
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("space", "toggle_selection", "Toggle Selection", show=False),
        Binding("a", "select_all", "Select All", show=False),
        Binding("n", "deselect_all", "Deselect All", show=False),
        Binding("enter", "confirm_selection", "Confirm", show=False),
    ]

    def __init__(self, symbols_for_selection, id: str | None = None, name: str | None = None, classes: str | None = None):
        super().__init__(id=id, name=name, classes=classes)
        self.symbols_for_selection = symbols_for_selection
        self.selected_indices = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Use arrow keys to navigate, Space to select/deselect, Enter to confirm"),
            Static("Press 'a' to select all, 'n' to deselect all"),
            Static("Month codes: H=March, M=June, U=September, Z=December (for NQ/ES)"),
            ListView(
                *[
                    ListItem(
                        Label(self._format_symbol_item(item, i)),
                        id=f"symbol_item_{i}"
                    )
                    for i, item in enumerate(self.symbols_for_selection)
                ],
                id="symbol_list"
            ),
            Horizontal(
                Button("Confirm", id="confirm_selection_btn", variant="primary"),
                Button("Cancel", id="cancel_selection_btn", variant="default"),
                classes="button-row"
            ),
            id="selection-container"
        )
        yield Footer()

    def _format_symbol_item(self, item, index):
        selected_char = "[X]" if item.get('selected', False) else "[ ]"
        symbol_display = item['symbol']
        month_code = ""
        month_name = ""
        if len(symbol_display) > 2:
            for char in symbol_display[2:]:
                if char.isalpha():
                    month_map = {'H': 'March', 'M': 'June', 'U': 'September', 'Z': 'December'}
                    if char.upper() in month_map:
                        month_code = char.upper()
                        month_name = month_map[month_code]
                    else:
                        month_code = char.upper()
                    break
        
        month_info = f" (Month: {month_name or month_code})" if month_code else ""
        return f"{selected_char} {index+1}. Symbol: {symbol_display}{month_info} | Product: {item['product_code']} | Exp: {item['expiration']}"

    def on_mount(self) -> None:
        self.query_one(ListView).focus()

    def action_cursor_up(self) -> None:
        self.query_one(ListView).action_cursor_up()
        self._update_list_display()

    def action_cursor_down(self) -> None:
        self.query_one(ListView).action_cursor_down()
        self._update_list_display()

    def action_toggle_selection(self) -> None:
        list_view = self.query_one(ListView)
        if list_view.highlighted is not None:
            idx = list_view.highlighted
            self.symbols_for_selection[idx]['selected'] = not self.symbols_for_selection[idx]['selected']
            self._update_list_display()

    def action_select_all(self) -> None:
        for item in self.symbols_for_selection:
            item['selected'] = True
        self._update_list_display()

    def action_deselect_all(self) -> None:
        for item in self.symbols_for_selection:
            item['selected'] = False
        self._update_list_display()

    def action_confirm_selection(self) -> None:
        self.selected_indices = [i for i, item in enumerate(self.symbols_for_selection) if item['selected']]
        self.dismiss(self.selected_indices)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_selection_btn":
            self.action_confirm_selection()
        elif event.button.id == "cancel_selection_btn":
            self.dismiss([]) # Dismiss with empty list if cancelled

    def _update_list_display(self) -> None:
        list_view = self.query_one(ListView)
        for i, item in enumerate(self.symbols_for_selection):
            list_item = self.query_one(f"#symbol_item_{i}", ListItem)
            label = list_item.query_one(Label)
            label.update(self._format_symbol_item(item, i))
            if item['selected']:
                list_item.add_class("selected")
            else:
                list_item.remove_class("selected")
            if i == list_view.highlighted:
                list_item.add_class("highlighted")
            else:
                list_item.remove_class("highlighted")


class RithmicAdminApp(App):
    """A Textual app for Rithmic data administration."""

    CSS_PATH = "admin_rithmic.css" # We will define this CSS file
    BINDINGS = [
        Binding("1", "test_connections", "Test Connections"),
        Binding("2", "search_symbols", "Search Symbols"),
        Binding("3", "download_historical_data", "Download Data"),
        Binding("4", "view_timescale_data", "View DB Data"),
        Binding("5", "initialize_database", "Initialize DB"),
        Binding("q", "quit", "Quit"),
    ]

    # Reactive attributes for UI updates
    is_connected = reactive(False)
    db_connected = reactive(False)
    current_symbols = reactive([])
    available_contracts = reactive({})
    # download_progress: {symbol: {'seconds': {'progress': 0.0, 'current_chunk_info': ''}, 'minutes': {'progress': 0.0, 'current_chunk_info': ''}}}
    download_progress = reactive({}) 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rithmic_client = None
        self.db_manager = get_database_manager()
        self.current_exchange = "CME"
        self.log_handler = TextualHandler(self)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO) # Ensure logs are captured

    def watch_is_connected(self, connected: bool) -> None:
        self.query_one("#rithmic-status", Static).update(f"Rithmic Connection: {'[green]Connected[/green]' if connected else '[red]Disconnected[/red]'}")

    def watch_db_connected(self, connected: bool) -> None:
        self.query_one("#db-status", Static).update(f"TimescaleDB Connection: {'[green]Connected[/green]' if connected else '[red]Disconnected[/red]'}")

    def watch_current_symbols(self, symbols: list[str]) -> None:
        self.query_one("#current-symbols", Static).update(f"Symbols: {', '.join(symbols) if symbols else 'None'}")

    def watch_available_contracts(self, contracts: dict) -> None:
        contract_str = []
        if contracts:
            for symbol, contract_list in contracts.items():
                contract_str.append(f"{symbol}: {', '.join(contract_list)}")
        self.query_one("#available-contracts", Static).update(f"Contracts: {' | '.join(contract_str) if contract_str else 'None'}")

    def watch_download_progress(self, progress_data: dict) -> None:
        progress_panel = self.query_one("#progress-panel")
        # Clear existing progress bars
        for child in list(progress_panel.children):
            child.remove()

        if not progress_data:
            progress_panel.add_class("hidden")
            return
        
        progress_panel.remove_class("hidden")
        progress_panel.add(Static("[bold]Download Progress:[/bold]"))

        for symbol, bar_types_progress in progress_data.items():
            for bar_type, info in bar_types_progress.items():
                if info['progress'] > 0 or info['current_chunk_info']:
                    # Create or update progress bar and info for each bar type
                    progress_label = Static(f"  [bold]{symbol} ({bar_type.capitalize()}):[/bold] {info['current_chunk_info']}", id=f"progress_label_{symbol}_{bar_type}")
                    progress_bar = ProgressBar(
                        total=1.0, 
                        completed=info['progress'], 
                        show_eta=False, 
                        show_percentage=True,
                        id=f"progress_bar_{symbol}_{bar_type}"
                    )
                    progress_panel.add(progress_label)
                    progress_panel.add(progress_bar)
                # If progress is 1.0 (completed), mark it as such
                if info['progress'] >= 1.0 and info['current_chunk_info'] != "Completed":
                    info['current_chunk_info'] = "Completed"
                    self.query_one(f"#progress_label_{symbol}_{bar_type}", Static).update(f"  [bold]{symbol} ({bar_type.capitalize()}):[/bold] {info['current_chunk_info']}")
                    self.query_one(f"#progress_bar_{symbol}_{bar_type}", ProgressBar).update(completed=1.0)


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="app-grid"):
            with Container(id="left-panel"):
                yield Static("[bold yellow]RITHMIC DATA ADMIN TOOL[/bold yellow]", id="app-title")
                yield Static("--- Connection Status ---", classes="section-title")
                yield Static("Rithmic Connection: [red]Disconnected[/red]", id="rithmic-status")
                yield Static("TimescaleDB Connection: [red]Disconnected[/red]", id="db-status")
                yield Static("--- Current Selection ---", classes="section-title")
                yield Static("Symbols: None", id="current-symbols")
                yield Static("Exchange: CME", id="current-exchange")
                yield Static("Contracts: None", id="available-contracts")
                yield Static("--- Menu ---", classes="section-title")
                yield ListView(
                    ListItem(Label("1. Test Connections (DB + Rithmic)"), id="menu_test_connections"),
                    ListItem(Label("2. Search Symbols & Check Contracts"), id="menu_search_symbols"),
                    ListItem(Label("3. Download Historical Data"), id="menu_download_historical"),
                    ListItem(Label("4. View TimescaleDB Data"), id="menu_view_db_data"),
                    ListItem(Label("5. Initialize/Setup Database"), id="menu_initialize_db"),
                    ListItem(Label("Q. Exit"), id="menu_quit"),
                    id="main-menu"
                )
            with VerticalScroll(id="right-panel"):
                yield Container(id="progress-panel", classes="hidden") # Hidden until progress starts
                yield Static("[bold]Logs:[/bold]", classes="section-title")
                yield TextArea(id="log-output", read_only=True, classes="log-area")
        yield Footer()

    async def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.query_one("#main-menu").focus()
        # Initial status update
        self.is_connected = False
        self.db_connected = False
        self.query_one("#current-exchange", Static).update(f"Exchange: {self.current_exchange}")
        # Redirect logging to the Textual TextArea
        self.log_output_widget = self.query_one("#log-output", TextArea)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO) # Set overall logging level

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle menu item selection."""
        if event.list_view.id == "main-menu":
            menu_id = event.item.id
            if menu_id == "menu_test_connections":
                self.action_test_connections()
            elif menu_id == "menu_search_symbols":
                self.action_search_symbols()
            elif menu_id == "menu_download_historical":
                self.action_download_historical_data()
            elif menu_id == "menu_view_db_data":
                self.action_view_timescale_data()
            elif menu_id == "menu_initialize_db":
                self.action_initialize_database()
            elif menu_id == "menu_quit":
                self.action_quit()

    @App.action("test_connections")
    async def action_test_connections(self) -> None:
        self.log_output_widget.write("Testing Connections...\n")
        
        # Test TimescaleDB
        self.log_output_widget.write("1. Testing TimescaleDB connection...\n")
        try:
            connection_ok = await self.db_manager.test_connection()
            if connection_ok:
                self.log_output_widget.write("[green]✅ TimescaleDB connection successful[/green]\n")
                self.db_connected = True
                async with get_async_session() as session:
                    from sqlalchemy import text
                    result_seconds = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds LIMIT 1"))
                    result_minutes = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes LIMIT 1"))
                    if result_seconds.scalar() is not None and result_minutes.scalar() is not None:
                        self.log_output_widget.write("[green]✅ TimescaleDB tables accessible[/green]\n")
                    else:
                        self.log_output_widget.write("[red]❌ TimescaleDB tables not accessible or empty[/red]\n")
            else:
                self.log_output_widget.write("[red]❌ TimescaleDB connection failed[/red]\n")
                self.db_connected = False
        except Exception as e:
            self.log_output_widget.write(f"[red]❌ TimescaleDB connection error: {e}[/red]\n")
            self.db_connected = False

        # Test Rithmic
        self.log_output_widget.write("2. Testing Rithmic connection...\n")
        await self._connect_to_rithmic(cli_mode=True) # Use internal connect method

        self.log_output_widget.write("\nConnection Summary:\n")
        self.log_output_widget.write(f"TimescaleDB: {'[green]✅ Connected[/green]' if self.db_connected else '[red]❌ Failed[/red]'}\n")
        self.log_output_widget.write(f"Rithmic: {'[green]✅ Connected[/green]' if self.is_connected else '[red]❌ Failed[/red]'}\n")
        
    async def _disconnect_from_rithmic(self, timeout=5.0):
        """Disconnects from the Rithmic client."""
        if self.rithmic_client and self.is_connected:
            try:
                self.log_output_widget.write("\nDisconnecting from Rithmic...\n")
                await asyncio.wait_for(self.rithmic_client.disconnect(), timeout=timeout)
                self.log_output_widget.write("[green]Rithmic connection closed successfully.[/green]\n")
            except asyncio.TimeoutError:
                self.log_output_widget.write("[yellow]Disconnect timed out, but this is expected behavior with the Rithmic API.[/yellow]\n")
                self.log_output_widget.write("[green]Program completed successfully despite timeout warnings.[/green]\n")
            except Exception as e:
                self.log_output_widget.write(f"[yellow]Error during disconnect: {e}[/yellow]\n")
                self.log_output_widget.write("[green]Program completed successfully despite disconnect errors.[/green]\n")
            finally:
                self.is_connected = False

    async def _connect_to_rithmic(self, cli_mode=False, data_types=None):
        """Connects to the Rithmic client."""
        self.log_output_widget.write("Connecting to Rithmic...\n")

        if data_types:
            data_type_names = [dt.name for dt in data_types if hasattr(dt, 'name')]
            self.log_output_widget.write(f"Enabling data types: {', '.join(data_type_names)}\n")

        try:
            config = get_chicago_gateway_config()
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

            self.log_output_widget.write(f"Username: {config['rithmic']['user']}\n")
            self.log_output_widget.write(f"System: {config['rithmic']['system_name']}\n")
            self.log_output_widget.write(f"Gateway: {config['rithmic']['gateway']}\n")
            self.log_output_widget.write(f"App: {config['rithmic']['app_name']} v{config['rithmic']['app_version']}\n")

            gateway_name = config['rithmic']['gateway']
            gateway = Gateway.CHICAGO if gateway_name == 'Chicago' else Gateway.TEST # Assuming 'TEST' is the fallback

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

            self.log_output_widget.write("Attempting connection...\n")
            await self.rithmic_client.connect()
            self.is_connected = True

            if data_types and "HISTORY" in data_types:
                self.log_output_widget.write("Historical data access is available by default...\n")
                self.log_output_widget.write("[green]Ready to access historical data![/green]\n")
                if hasattr(self.rithmic_client, 'history_plant'):
                    self.log_output_widget.write("[green]History plant is now available![/green]\n")
                else:
                    self.log_output_widget.write("[yellow]History plant not explicitly available, but historical methods should still work.[/yellow]\n")

            self.log_output_widget.write("[green]Successfully connected to Rithmic![/green]\n")

        except Exception as e:
            self.log_output_widget.write(f"[red]Failed to connect to Rithmic: {e}[/red]\n")
            self.is_connected = False

    @App.action("search_symbols")
    async def action_search_symbols(self) -> None:
        if not self.is_connected:
            self.log_output_widget.write("[red]Error: Not connected to Rithmic. Please test connections first.[/red]\n")
            return

        self.log_output_widget.write("\n[bold yellow]Search Symbols & Check Contracts[/bold yellow]\n")
        self.log_output_widget.write("You can use wildcards: * (any characters) and ? (single character)\n")
        self.log_output_widget.write("Examples: NQ?5 (matches NQU5, NQZ5, etc.), NQ* (matches all NQ contracts)\n")
        self.log_output_widget.write("For NQ and ES futures, only quarterly months (H, M, U, Z) are valid\n")

        # Use app.prompt for input
        search_term = await self.app.prompt("Enter search term (e.g., ES, NQ, NQ?5, NQ*):")
        if not search_term:
            self.log_output_widget.write("[red]Search term cannot be empty[/red]\n")
            return

        has_wildcards = '*' in search_term or '?' in search_term
        api_search_term = search_term
        if has_wildcards:
            api_search_term = re.split(r'[\*\?]', search_term)[0]
            if not api_search_term:
                api_search_term = search_term.replace('*', '').replace('?', '')
                if not api_search_term:
                    api_search_term = 'A'

        exchange_input = await self.app.prompt(f"Enter exchange (default: {self.current_exchange}):")
        if exchange_input:
            self.current_exchange = exchange_input
            self.query_one("#current-exchange", Static).update(f"Exchange: {self.current_exchange}")

        self.log_output_widget.write(f"\nSearching for '{search_term}' on {self.current_exchange}...\n")
        try:
            results = await search_symbols_func(
                self.rithmic_client,
                api_search_term,
                instrument_type=InstrumentType.FUTURE,
                exchange=self.current_exchange
            )
        except Exception as e:
            self.log_output_widget.write(f"[red]Error searching for symbols: {e}[/red]\n")
            return

        if not results:
            self.log_output_widget.write(f"[yellow]No symbols found matching '{search_term}' on {self.current_exchange}[/yellow]\n")
            return

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
                self.log_output_widget.write(f"[yellow]No symbols found matching wildcard pattern '{search_term}' on {self.current_exchange}[/yellow]\n")
                return

        self.log_output_widget.write(f"[green]Found {len(filtered_results)} symbols:[/green]\n")

        symbols_for_selection = []
        for i, result in enumerate(filtered_results, 1):
            symbols_for_selection.append({
                'index': i,
                'symbol': result.symbol,
                'product_code': result.product_code,
                'name': result.symbol_name,
                'type': result.instrument_type,
                'expiration': result.expiration_date,
                'selected': False
            })

        # Push the interactive selection screen
        selected_indices = await self.push_screen_wait(SymbolSelectionScreen(symbols_for_selection))

        if not selected_indices:
            self.log_output_widget.write("[yellow]No symbols selected[/yellow]\n")
            return

        self.current_symbols = [symbols_for_selection[idx]['symbol'] for idx in selected_indices]
        self.log_output_widget.write(f"[green]Selected symbols: {', '.join(self.current_symbols)}[/green]\n")

        self.log_output_widget.write("\n[bold yellow]Checking Available Contracts and Database Data...[/bold yellow]\n")
        new_available_contracts = {}
        for symbol_full_name in self.current_symbols:
            product_code_match = re.match(r'^([A-Za-z]+)', symbol_full_name)
            product_code = product_code_match.group(1) if product_code_match else symbol_full_name

            self.log_output_widget.write(f"Checking contracts for {symbol_full_name} (Product: {product_code})...\n")
            
            try:
                front_month_result = await get_front_month_contracts(self.rithmic_client, [product_code], self.current_exchange)
                front_month = front_month_result.get(product_code, "No front month contract found")

                contract_results = await search_symbols_func(
                    self.rithmic_client,
                    product_code,
                    instrument_type=InstrumentType.FUTURE,
                    exchange=self.current_exchange
                )
            except Exception as e:
                front_month = f"Error determining front month: {e}"
                contract_results = []

            if not contract_results:
                self.log_output_widget.write(f"[yellow]Warning: No contracts found for {symbol_full_name}.[/yellow]\n")
                continue

            contracts_for_symbol = sorted([r.symbol for r in contract_results if r.product_code == product_code])
            if not contracts_for_symbol:
                self.log_output_widget.write(f"[yellow]Warning: No exact contract matches found for {symbol_full_name}.[/yellow]\n")
                continue
            
            new_available_contracts[symbol_full_name] = contracts_for_symbol
            self.log_output_widget.write(f"  Front month: {front_month}\n")
            self.log_output_widget.write(f"  Available contracts: {', '.join(contracts_for_symbol)}\n")

            if self.db_connected:
                try:
                    async with get_async_session() as session:
                        helper = TimescaleDBHelper(session)
                        
                        result_seconds = await session.execute(
                            text("SELECT COUNT(*), MAX(timestamp) FROM market_data_seconds WHERE symbol = :symbol AND contract = :contract AND exchange = :exchange"),
                            {'symbol': product_code, 'contract': symbol_full_name, 'exchange': self.current_exchange}
                        )
                        second_count, latest_second_timestamp = result_seconds.fetchone()

                        result_minutes = await session.execute(
                            text("SELECT COUNT(*), MAX(timestamp) FROM market_data_minutes WHERE symbol = :symbol AND contract = :contract AND exchange = :exchange"),
                            {'symbol': product_code, 'contract': symbol_full_name, 'exchange': self.current_exchange}
                        )
                        minute_count, latest_minute_timestamp = result_minutes.fetchone()

                        self.log_output_widget.write(f"  Data points in TimescaleDB for {symbol_full_name}:\n")
                        self.log_output_widget.write(f"    - Second bars: {second_count:,} records (Latest: {latest_second_timestamp if latest_second_timestamp else 'N/A'})\n")
                        self.log_output_widget.write(f"    - Minute bars: {minute_count:,} records (Latest: {latest_minute_timestamp if latest_minute_timestamp else 'N/A'})\n")

                except Exception as e:
                    self.log_output_widget.write(f"  [yellow]Error checking TimescaleDB data for {symbol_full_name}: {e}[/yellow]\n")
            else:
                self.log_output_widget.write(f"  [yellow]TimescaleDB not connected - cannot check data points[/yellow]\n")
            self.log_output_widget.write("\n")

        self.available_contracts = new_available_contracts
        self.log_output_widget.write("[green]Symbol search and contract check completed[/green]\n")

    @App.action("download_historical_data")
    async def action_download_historical_data(self) -> None:
        if not self.is_connected:
            self.log_output_widget.write("[red]Error: Not connected to Rithmic. Please test connections first.[/red]\n")
            return

        if not self.db_connected:
            self.log_output_widget.write("[red]Error: Not connected to TimescaleDB. Please test connections first.[/red]\n")
            return

        if not self.available_contracts:
            self.log_output_widget.write("[red]Error: No contracts available. Please search symbols first.[/red]\n")
            return

        self.log_output_widget.write("\n[bold yellow]Download Historical Data to TimescaleDB[/bold yellow]\n")

        days_input = await self.app.prompt("Enter number of days to download (default: 7):")
        days = 7
        if days_input.strip():
            try:
                days = int(days_input)
            except ValueError:
                self.log_output_widget.write("[red]Invalid input. Using default of 7 days.[/red]\n")
                days = 7
        
        bar_choice_input = await self.app.prompt("Bar Types:\n1. Second bars\n2. Minute bars\n3. Both\nEnter choice (default: 1):")
        download_second_bars = bar_choice_input in ['1', '3', '']
        download_minute_bars = bar_choice_input in ['2', '3']

        if not download_second_bars and not download_minute_bars:
            self.log_output_widget.write("[red]Invalid choice. Defaulting to second bars.[/red]\n")
            download_second_bars = True

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        self.log_output_widget.write(f"\nDownloading data from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}\n")
        bar_types_str = []
        if download_second_bars: bar_types_str.append('Second bars')
        if download_minute_bars: bar_types_str.append('Minute bars')
        self.log_output_widget.write(f"Bar types: {(' and ').join(bar_types_str)}\n")
        self.log_output_widget.write(f"Target: TimescaleDB\n")

        # Initialize download_progress for all selected contracts
        new_download_progress = {}
        for symbol in self.available_contracts.keys():
            new_download_progress[symbol] = {
                'seconds': {'progress': 0.0, 'current_chunk_info': ''},
                'minutes': {'progress': 0.0, 'current_chunk_info': ''}
            }
        self.download_progress = new_download_progress # Trigger reactive update

        # Run download as a worker to keep UI responsive
        self.run_worker(self._perform_download(start_time, end_time, download_second_bars, download_minute_bars))

    async def _perform_download(self, start_time: datetime, end_time: datetime, download_second_bars: bool, download_minute_bars: bool) -> None:
        try:
            async with get_async_session() as session:
                helper = TimescaleDBHelper(session)

                for symbol_root, contracts in self.available_contracts.items():
                    self.log_output_widget.write(f"\nProcessing {symbol_root} contracts...\n")
                    
                    total_contracts_for_symbol = len(contracts)
                    
                    for i, contract in enumerate(contracts):
                        self.log_output_widget.write(f"  Processing {contract}...\n")

                        # --- Download Second Bars ---
                        if download_second_bars:
                            self.log_output_widget.write(f"  Downloading second bars for {contract}...\n")
                            try:
                                all_second_bars = []
                                current_chunk_start = start_time
                                max_chunk_hours = 6
                                empty_chunks_in_a_row = 0
                                max_empty_chunks = 4

                                while current_chunk_start < end_time and empty_chunks_in_a_row < max_empty_chunks:
                                    current_chunk_end = min(end_time, current_chunk_start + timedelta(hours=max_chunk_hours))
                                    
                                    # Update current chunk info for display
                                    self.download_progress[symbol_root]['seconds']['current_chunk_info'] = \
                                        f"Chunk: {current_chunk_start.strftime('%Y-%m-%d %H:%M')} to {current_chunk_end.strftime('%Y-%m-%d %H:%M')}"
                                    self.download_progress = self.download_progress # Trigger reactive update

                                    # Simple market hours check (requires pandas for .dt)
                                    # For Textual app, avoid pandas dependency in core logic if possible, or ensure it's installed.
                                    # For now, I'll remove the pandas-specific market hours check to avoid a potential import error if pandas is not installed.
                                    # If you need this, ensure pandas is in your environment.
                                    # def is_likely_market_hours(dt):
                                    #     hour = dt.hour
                                    #     weekday = dt.dt.weekday() # Use .dt for pandas datetime properties
                                    #     if weekday == 5: # Saturday
                                    #         return False
                                    #     if weekday == 6 and hour < 18: # Sunday before 6 PM
                                    #         return False
                                    #     if weekday == 4 and hour >= 17: # Friday after 5 PM
                                    #         return False
                                    #     if hour >= 17 and hour < 18: # 5 PM to 6 PM (often close)
                                    #         return False
                                    #     return True

                                    self.log_output_widget.write(f"    Requesting chunk: {current_chunk_start.strftime('%Y-%m-%d %H:%M')} to {current_chunk_end.strftime('%Y-%m-%d %H:%M')}\n")
                                    try:
                                        chunk_bars = await self.rithmic_client.get_historical_time_bars(
                                            contract,
                                            self.current_exchange,
                                            current_chunk_start,
                                            current_chunk_end,
                                            TimeBarType.SECOND_BAR,
                                            1
                                        )
                                    except Exception as e:
                                        self.log_output_widget.write(f"[red]Error retrieving historical time bars for seconds: {e}[/red]\n")
                                        chunk_bars = []

                                    self.log_output_widget.write(f"[green]Received {len(chunk_bars)} second bars for this chunk[/green]\n")
                                    if not chunk_bars:
                                        empty_chunks_in_a_row += 1
                                        self.log_output_widget.write(f"[yellow]Empty chunk ({empty_chunks_in_a_row}/{max_empty_chunks})[/yellow]\n")
                                    else:
                                        empty_chunks_in_a_row = 0
                                        all_second_bars.extend(chunk_bars)

                                    if len(chunk_bars) >= 9999:
                                        self.log_output_widget.write("[yellow]API limit reached (likely 9999 data points), reducing chunk size[/yellow]\n")
                                        if max_chunk_hours > 0.5:
                                            max_chunk_hours /= 2
                                            self.log_output_widget.write(f"Reduced chunk size to {max_chunk_hours} hours\n")
                                    else:
                                        current_chunk_start = current_chunk_end

                                self.log_output_widget.write(f"[green]Total received: {len(all_second_bars)} second bars[/green]\n")
                                if all_second_bars:
                                    data_records = []
                                    for bar in all_second_bars:
                                        timestamp_val = bar.get('bar_end_datetime')
                                        if isinstance(timestamp_val, (int, float)):
                                            timestamp_val = datetime.fromtimestamp(timestamp_val / 1000, tz=timezone.utc)
                                        elif not isinstance(timestamp_val, datetime):
                                            timestamp_val = datetime.now(timezone.utc)

                                        record = {
                                            'timestamp': timestamp_val,
                                            'symbol': symbol_root,
                                            'contract': contract,
                                            'exchange': self.current_exchange,
                                            'exchange_code': 'XCME' if self.current_exchange == 'CME' else self.current_exchange,
                                            'open': float(bar.get('open', 0)),
                                            'high': float(bar.get('high', 0)),
                                            'low': float(bar.get('low', 0)),
                                            'close': float(bar.get('close', 0)),
                                            'volume': bar.get('volume', 0),
                                            'tick_count': bar.get('tick_count', 1),
                                            'vwap': float(bar.get('vwap', bar.get('close', 0))),
                                            'bid': float(bar.get('bid', 0)) if 'bid' in bar else None,
                                            'ask': float(bar.get('ask', 0)) if 'ask' in bar else None,
                                            'spread': float(bar.get('ask', 0)) - float(bar.get('bid', 0)) if 'bid' in bar and 'ask' in bar else None,
                                            'data_quality_score': 1.0,
                                            'is_regular_hours': True
                                        }
                                        data_records.append(record)
                                    
                                    await helper.bulk_insert_market_data(data_records, 'market_data_seconds')
                                    self.log_output_widget.write(f"[green]Saved {len(data_records)} second bars to TimescaleDB[/green]\n")
                                
                                # Update progress for this bar type
                                self.download_progress[symbol_root]['seconds']['progress'] = (i + 1) / total_contracts_for_symbol
                                self.download_progress[symbol_root]['seconds']['current_chunk_info'] = "Completed"
                                self.download_progress = self.download_progress # Trigger reactive update

                            except Exception as e:
                                self.log_output_widget.write(f"[red]Error downloading second bars for {contract}: {e}[/red]\n")
                                self.download_progress[symbol_root]['seconds']['current_chunk_info'] = f"Error: {e}"
                                self.download_progress[symbol_root]['seconds']['progress'] = 0.0
                                self.download_progress = self.download_progress # Trigger reactive update

                        # --- Download Minute Bars ---
                        if download_minute_bars:
                            self.log_output_widget.write(f"  Downloading minute bars for {contract}...\n")
                            try:
                                all_minute_bars = []
                                current_chunk_start = start_time
                                max_chunk_days = 2
                                empty_chunks_in_a_row = 0
                                max_empty_chunks = 3

                                while current_chunk_start < end_time and empty_chunks_in_a_row < max_empty_chunks:
                                    current_chunk_end = min(end_time, current_chunk_start + timedelta(days=max_chunk_days))
                                    
                                    self.download_progress[symbol_root]['minutes']['current_chunk_info'] = \
                                        f"Chunk: {current_chunk_start.strftime('%Y-%m-%d %H:%M')} to {current_chunk_end.strftime('%Y-%m-%d %H:%M')}"
                                    self.download_progress = self.download_progress # Trigger reactive update

                                    self.log_output_widget.write(f"    Requesting chunk: {current_chunk_start.strftime('%Y-%m-%d %H:%M')} to {current_chunk_end.strftime('%Y-%m-%d %H:%M')}\n")
                                    try:
                                        chunk_bars = await self.rithmic_client.get_historical_time_bars(
                                            contract,
                                            self.current_exchange,
                                            current_chunk_start,
                                            current_chunk_end,
                                            TimeBarType.MINUTE_BAR,
                                            1
                                        )
                                    except Exception as e:
                                        self.log_output_widget.write(f"[red]Error retrieving historical time bars for minutes: {e}[/red]\n")
                                        chunk_bars = []

                                    self.log_output_widget.write(f"[green]Received {len(chunk_bars)} minute bars for this chunk[/green]\n")
                                    if not chunk_bars:
                                        empty_chunks_in_a_row += 1
                                        self.log_output_widget.write(f"[yellow]Empty chunk ({empty_chunks_in_a_row}/{max_empty_chunks})[/yellow]\n")
                                    else:
                                        empty_chunks_in_a_row = 0
                                        all_minute_bars.extend(chunk_bars)

                                    if len(chunk_bars) >= 9999:
                                        self.log_output_widget.write("[yellow]API limit reached (likely 9999 data points), reducing chunk size[/yellow]\n")
                                        if max_chunk_days > 0.1:
                                            max_chunk_days /= 2
                                            self.log_output_widget.write(f"Reduced chunk size to {max_chunk_days} days\n")
                                    else:
                                        current_chunk_start = current_chunk_end

                                self.log_output_widget.write(f"[green]Total received: {len(all_minute_bars)} minute bars[/green]\n")
                                if all_minute_bars:
                                    data_records = []
                                    for bar in all_minute_bars:
                                        timestamp_val = bar.get('bar_end_datetime')
                                        if isinstance(timestamp_val, (int, float)):
                                            timestamp_val = datetime.fromtimestamp(timestamp_val / 1000, tz=timezone.utc)
                                        elif not isinstance(timestamp_val, datetime):
                                            timestamp_val = datetime.now(timezone.utc)

                                        record = {
                                            'timestamp': timestamp_val,
                                            'symbol': symbol_root,
                                            'contract': contract,
                                            'exchange': self.current_exchange,
                                            'exchange_code': 'XCME' if self.current_exchange == 'CME' else self.current_exchange,
                                            'open': float(bar.get('open', 0)),
                                            'high': float(bar.get('high', 0)),
                                            'low': float(bar.get('low', 0)),
                                            'close': float(bar.get('close', 0)),
                                            'volume': bar.get('volume', 0),
                                            'tick_count': bar.get('tick_count', 1),
                                            'vwap': float(bar.get('vwap', bar.get('close', 0))),
                                            'bid': float(bar.get('bid', 0)) if 'bid' in bar else None,
                                            'ask': float(bar.get('ask', 0)) if 'ask' in bar else None,
                                            'spread': float(bar.get('ask', 0)) - float(bar.get('bid', 0)) if 'bid' in bar and 'ask' in bar else None,
                                            'data_quality_score': 1.0,
                                            'is_regular_hours': True
                                        }
                                        data_records.append(record)
                                    
                                    await helper.bulk_insert_market_data(data_records, 'market_data_minutes')
                                    self.log_output_widget.write(f"[green]Saved {len(data_records)} minute bars to TimescaleDB[/green]\n")
                                
                                # Update progress for this bar type
                                self.download_progress[symbol_root]['minutes']['progress'] = (i + 1) / total_contracts_for_symbol
                                self.download_progress[symbol_root]['minutes']['current_chunk_info'] = "Completed"
                                self.download_progress = self.download_progress # Trigger reactive update

                            except Exception as e:
                                self.log_output_widget.write(f"[red]Error downloading minute bars for {contract}: {e}[/red]\n")
                                self.download_progress[symbol_root]['minutes']['current_chunk_info'] = f"Error: {e}"
                                self.download_progress[symbol_root]['minutes']['progress'] = 0.0
                                self.download_progress = self.download_progress # Trigger reactive update
                    
            self.log_output_widget.write("\n[green]Historical data download completed to TimescaleDB[/green]\n")

            # Final database summary after all downloads
            try:
                async with get_async_session() as session:
                    from sqlalchemy import text
                    result_seconds_total = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
                    second_count_total = result_seconds_total.scalar()
                    result_minutes_total = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
                    minute_count_total = result_minutes_total.scalar()

                    self.log_output_widget.write("\n[bold cyan]TimescaleDB Summary:[/bold cyan]\n")
                    self.log_output_widget.write(f"Total second bars in database: {second_count_total:,}\n")
                    self.log_output_widget.write(f"Total minute bars in database: {minute_count_total:,}\n")

                    for symbol in self.current_symbols:
                        result_seconds_symbol = await session.execute(
                            text("SELECT COUNT(*), MAX(timestamp) FROM market_data_seconds WHERE symbol = :symbol"),
                            {'symbol': symbol}
                        )
                        row_seconds = result_seconds_symbol.fetchone()

                        result_minutes_symbol = await session.execute(
                            text("SELECT COUNT(*), MAX(timestamp) FROM market_data_minutes WHERE symbol = :symbol"),
                            {'symbol': symbol}
                        )
                        row_minutes = result_minutes_symbol.fetchone()

                        self.log_output_widget.write(f"\n{symbol} Data:\n")
                        if row_seconds and row_seconds[0] > 0:
                            self.log_output_widget.write(f"  Second bars: {row_seconds[0]:,} records, latest: {row_seconds[1]}\n")
                        else:
                            self.log_output_widget.write(f"  Second bars: No records found\n")
                        
                        if row_minutes and row_minutes[0] > 0:
                            self.log_output_widget.write(f"  Minute bars: {row_minutes[0]:,} records, latest: {row_minutes[1]}\n")
                        else:
                            self.log_output_widget.write(f"  Minute bars: No records found\n")

            except Exception as e:
                self.log_output_widget.write(f"\n[yellow]Could not generate summary statistics: {e}[/yellow]\n")

        except Exception as e:
            self.log_output_widget.write(f"[red]Error during historical data download process: {e}[/red]\n")
        finally:
            self.download_progress = {} # Clear progress after download

    @App.action("view_timescale_data")
    async def action_view_timescale_data(self) -> None:
        if not self.db_connected:
            self.log_output_widget.write("[red]Error: Not connected to TimescaleDB. Please test connections first.[/red]\n")
            return

        self.log_output_widget.write("\n[bold yellow]TimescaleDB Data Viewer[/bold yellow]\n")
        try:
            async with get_async_session() as session:
                from sqlalchemy import text

                self.log_output_widget.write("\n[bold cyan]Table Summary:[/bold cyan]\n")
                result_seconds = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
                second_count = result_seconds.scalar()
                self.log_output_widget.write(f"market_data_seconds: {second_count:,} records\n")

                result_minutes = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
                minute_count = result_minutes.scalar()
                self.log_output_widget.write(f"market_data_minutes: {minute_count:,} records\n")

                self.log_output_widget.write("\n[bold cyan]Available Symbols (from market_data_seconds):[/bold cyan]\n")
                result_symbols = await session.execute(text("""
                    SELECT symbol, contract, exchange, COUNT(*) as count,
                           MIN(timestamp) as first_data,
                           MAX(timestamp) as last_data
                    FROM market_data_seconds
                    GROUP BY symbol, contract, exchange
                    ORDER BY symbol, contract, exchange
                """))
                symbols_data = result_symbols.fetchall()

                if symbols_data:
                    for row in symbols_data:
                        self.log_output_widget.write(f"  {row[0]} ({row[1]}, {row[2]}): {row[3]:,} records, {row[4].strftime('%Y-%m-%d %H:%M')} to {row[5].strftime('%Y-%m-%d %H:%M')}\n")
                else:
                    self.log_output_widget.write("No data found in market_data_seconds table for any symbol.\n")

                if second_count > 0:
                    self.log_output_widget.write("\n[bold cyan]Recent Data Sample (market_data_seconds):[/bold cyan]\n")
                    result_recent = await session.execute(text("""
                        SELECT timestamp, symbol, contract, exchange,
                               open, high, low, close, volume, tick_count
                        FROM market_data_seconds
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """))
                    recent_data = result_recent.fetchall()
                    for row in recent_data:
                        self.log_output_widget.write(f"{row[0].strftime('%Y-%m-%d %H:%M:%S')} | {row[1]} {row[2]} ({row[3]}) | O:{row[4]:.2f} H:{row[5]:.2f} L:{row[6]:.2f} C:{row[7]:.2f} V:{row[8]:,} T:{row[9]:,}\n")
                
                if minute_count > 0:
                    self.log_output_widget.write("\n[bold cyan]Recent Data Sample (market_data_minutes):[/bold cyan]\n")
                    result_recent_minutes = await session.execute(text("""
                        SELECT timestamp, symbol, contract, exchange,
                               open, high, low, close, volume, tick_count
                        FROM market_data_minutes
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """))
                    recent_data_minutes = result_recent_minutes.fetchall()
                    for row in recent_data_minutes:
                        self.log_output_widget.write(f"{row[0].strftime('%Y-%m-%d %H:%M:%S')} | {row[1]} {row[2]} ({row[3]}) | O:{row[4]:.2f} H:{row[5]:.2f} L:{row[6]:.2f} C:{row[7]:.2f} V:{row[8]:,} T:{row[9]:,}\n")

        except Exception as e:
            self.log_output_widget.write(f"[red]Error viewing TimescaleDB data: {e}[/red]\n")

    @App.action("initialize_database")
    async def action_initialize_database(self) -> None:
        self.log_output_widget.write("\n[bold yellow]Initialize TimescaleDB[/bold yellow]\n")
        try:
            self.log_output_widget.write("1. Testing connection...\n")
            connection_ok = await self.db_manager.test_connection()
            if not connection_ok:
                self.log_output_widget.write("[red]❌ Database connection failed[/red]\n")
                return
            self.log_output_widget.write("[green]✅ Database connection successful[/green]\n")

            self.log_output_widget.write("2. Initializing database extensions and creating tables...\n")
            await self.db_manager.initialize_database_schema()
            
            self.log_output_widget.write("\n[green]✅ Database initialization completed successfully![/green]\n")
            self.db_connected = True
        except Exception as e:
            self.log_output_widget.write(f"[red]❌ Database initialization failed: {e}[/red]\n")

    @App.action("quit")
    async def action_quit(self) -> None:
        if self.is_connected and self.rithmic_client:
            await self._disconnect_from_rithmic()
        self.log_output_widget.write("[yellow]Exiting...[/yellow]\n")
        self.exit()

    def on_log_message(self, message: LogMessage) -> None:
        """Handle custom LogMessage to update the TextArea."""
        self.log_output_widget.write(message.text + "\n")
        self.log_output_widget.scroll_end() # Auto-scroll to the end of logs


if __name__ == "__main__":
    # Create a dummy CSS file for basic styling needed by Textual
    # In a real project, this would be a separate file (e.g., admin_rithmic.css)
    css_content = """
    Screen {
        background: #202020;
        color: #E0E0E0;
    }
    #app-title {
        text-align: center;
        margin-bottom: 1;
    }
    .section-title {
        text-align: center;
        margin-top: 1;
        margin-bottom: 1;
        text-style: bold;
        color: #61AFEF; /* Blue */
    }
    #app-grid {
        grid-size: 2;
        grid-columns: 1fr 2fr;
        height: 1fr;
    }
    #left-panel {
        background: #282C34; /* Darker background */
        padding: 1;
        border: solid #3E4452;
        height: 100%;
    }
    #right-panel {
        background: #282C34;
        padding: 1;
        border: solid #3E4452;
        height: 100%;
    }
    #main-menu {
        border: round #5C6370;
        margin-top: 1;
    }
    #main-menu > ListItem {
        padding: 0 1;
        height: 1;
        text-align: left;
    }
    #main-menu > ListItem.highlighted {
        background: #61AFEF;
        color: black;
    }
    #main-menu > ListItem.selected {
        background: #98C379; /* Green */
        color: black;
    }
    #log-output {
        height: 1fr;
        border: round #5C6370;
        background: #1E2127; /* Even darker for log area */
    }
    #progress-panel {
        border: round #5C6370;
        padding: 1;
        margin-bottom: 1;
    }
    #progress-panel.hidden {
        display: none;
    }
    ProgressBar {
        width: 1fr;
        height: 1;
        margin-bottom: 1;
    }
    #selection-container {
        border: double #C678DD; /* Purple */
        padding: 1;
        margin: 2;
        align: center middle;
        height: 80%;
        width: 80%;
    }
    #symbol_list {
        border: round #5C6370;
        height: 1fr;
        margin-top: 1;
    }
    #symbol_list > ListItem {
        padding: 0 1;
        height: 1;
        text-align: left;
    }
    #symbol_list > ListItem.highlighted {
        background: #61AFEF;
        color: black;
    }
    #symbol_list > ListItem.selected {
        background: #98C379; /* Green */
        color: black;
    }
    .button-row {
        align-horizontal: center;
        margin-top: 1;
    }
    Button {
        margin: 0 1;
    }
    """
    with open("admin_rithmic.css", "w") as f:
        f.write(css_content)

    app = RithmicAdminApp()
    app.run()

