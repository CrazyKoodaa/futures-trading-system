import os
import time
import asyncio
import logging
import re
import fnmatch
from datetime import datetime, timedelta
import colorama
from colorama import Fore, Style
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from async_rithmic import RithmicClient, TimeBarType, InstrumentType, Gateway, DataType
from async_rithmic import ReconnectionSettings, RetrySettings
from config.chicago_gateway_config import get_chicago_gateway_config

# Import TimescaleDB connection
from shared.database.connection import get_async_session, TimescaleDBHelper, get_database_manager

# Initialize colorama
colorama.init()

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

# State variables
current_symbols = []
current_exchange = "CME"
available_contracts = {}
download_progress = {}
rithmic_client = None
is_connected = False
db_connected = False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print(f"{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.YELLOW}{'RITHMIC DATA ADMIN TOOL':^80}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    # Connection status
    if is_connected:
        print(f"{Fore.GREEN}Rithmic Connection: Connected{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Rithmic Connection: Disconnected{Style.RESET_ALL}")
    
    # Database connection status
    if db_connected:
        print(f"{Fore.GREEN}TimescaleDB Connection: Connected{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}TimescaleDB Connection: Disconnected{Style.RESET_ALL}")
    
    # Current symbols and exchange
    if current_symbols:
        print(f"{Fore.WHITE}Symbols: {', '.join(current_symbols)}")
    else:
        print(f"{Fore.WHITE}Symbols: None")
    print(f"Exchange: {current_exchange}")
    
    # Available contracts
    if available_contracts:
        contract_str = []
        for symbol, contracts in available_contracts.items():
            contract_str.append(f"{symbol}: {', '.join(contracts)}")
        print(f"Contracts: {' | '.join(contract_str)}")
    else:
        print("Contracts: None")
    
    # Download progress
    if download_progress:
        print("\nDownload Progress:")
        for symbol, progress in download_progress.items():
            progress_bar = "#" * int(progress * 30) + "." * (30 - int(progress * 30))
            print(f"{symbol}: [{progress_bar}] {progress*100:.1f}%")
    
    print(f"{Fore.CYAN}{'-' * 80}{Style.RESET_ALL}\n")

async def test_connections(cli_mode=False):
    """Test both database and Rithmic connections"""
    global db_connected, is_connected
    
    if not cli_mode:
        print_header()
    
    print(f"{Fore.YELLOW}Testing Connections...{Style.RESET_ALL}")
    
    # Test TimescaleDB connection
    print(f"{Fore.CYAN}1. Testing TimescaleDB connection...{Style.RESET_ALL}")
    try:
        db_manager = get_database_manager()
        connection_ok = await db_manager.test_connection()
        
        if connection_ok:
            print(f"{Fore.GREEN}✅ TimescaleDB connection successful{Style.RESET_ALL}")
            db_connected = True
            
            # Test table existence
            async with get_async_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds LIMIT 1"))
                print(f"{Fore.GREEN}✅ TimescaleDB tables accessible{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ TimescaleDB connection failed{Style.RESET_ALL}")
            db_connected = False
    except Exception as e:
        print(f"{Fore.RED}❌ TimescaleDB connection error: {e}{Style.RESET_ALL}")
        db_connected = False
    
    # Test Rithmic connection
    print(f"{Fore.CYAN}2. Testing Rithmic connection...{Style.RESET_ALL}")
    await connect_to_rithmic(cli_mode=True)
    
    # Summary
    print(f"\n{Fore.CYAN}Connection Summary:{Style.RESET_ALL}")
    print(f"TimescaleDB: {'✅ Connected' if db_connected else '❌ Failed'}")
    print(f"Rithmic: {'✅ Connected' if is_connected else '❌ Failed'}")
    
    if not cli_mode:
        input("\nPress Enter to continue...")

async def disconnect_from_rithmic(timeout=5.0):
    global rithmic_client, is_connected
    if rithmic_client and is_connected:
        try:
            print(f"\n{Fore.YELLOW}Disconnecting from Rithmic...{Style.RESET_ALL}")
            import sys
            from io import StringIO
            original_stderr = sys.stderr
            string_buffer = StringIO()
            try:
                sys.stderr = string_buffer
                await asyncio.wait_for(rithmic_client.disconnect(), timeout=timeout)
            finally:
                sys.stderr = original_stderr
            print(f"{Fore.GREEN}Rithmic connection closed successfully.{Style.RESET_ALL}")
        except asyncio.TimeoutError:
            print(f"{Fore.YELLOW}Disconnect timed out, but this is expected behavior with the Rithmic API.{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Program completed successfully despite timeout warnings.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}Error during disconnect: {e}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Program completed successfully despite disconnect errors.{Style.RESET_ALL}")
        finally:
            is_connected = False

async def connect_to_rithmic(cli_mode=False, data_types=None):
    global rithmic_client, is_connected
    if not cli_mode:
        print_header()
    print(f"{Fore.YELLOW}Connecting to Rithmic...{Style.RESET_ALL}")
    
    if data_types:
        data_type_names = [dt.name for dt in data_types]
        print(f"{Fore.CYAN}Enabling data types: {', '.join(data_type_names)}{Style.RESET_ALL}")
    
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
        
        print(f"Username: {config['rithmic']['user']}")
        print(f"System: {config['rithmic']['system_name']}")
        print(f"Gateway: {config['rithmic']['gateway']}")
        print(f"App: {config['rithmic']['app_name']} v{config['rithmic']['app_version']}")
        
        gateway_name = config['rithmic']['gateway']
        gateway = Gateway.CHICAGO if gateway_name == 'Chicago' else Gateway.TEST
        
        rithmic_client = RithmicClient(
            user=config['rithmic']['user'],
            password=config['rithmic']['password'],
            system_name=config['rithmic']['system_name'],
            app_name=config['rithmic']['app_name'],
            app_version=config['rithmic']['app_version'],
            gateway=gateway,
            reconnection_settings=reconnection,
            retry_settings=retry
        )
        
        print("\nAttempting connection...")
        await rithmic_client.connect()
        is_connected = True
        
        if data_types and 'HISTORY' in [dt for dt in data_types]:
            print(f"{Fore.CYAN}Historical data access is available by default...{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Ready to access historical data!{Style.RESET_ALL}")
            if hasattr(rithmic_client, 'history_plant'):
                print(f"{Fore.GREEN}History plant is now available!{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}History plant not available. Will try alternative methods.{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}Successfully connected to Rithmic!{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Failed to connect to Rithmic: {e}{Style.RESET_ALL}")
        is_connected = False
    
    if not cli_mode:
        input("\nPress Enter to continue...")

async def search_and_check_symbols():
    """Combined symbol search and contract checking"""
    global current_symbols, current_exchange, available_contracts
    from search_symbols import search_symbols as search_symbols_func
    
    if not is_connected:
        print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please test connections first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    print_header()
    print(f"{Fore.YELLOW}Search Symbols & Check Contracts{Style.RESET_ALL}")
    print(f"You can use wildcards: * (any characters) and ? (single character)")
    print(f"Examples: NQ?5 (matches NQU5, NQZ5, etc.), NQ* (matches all NQ contracts)")
    print(f"For NQ and ES futures, only quarterly months (H, M, U, Z) are valid")
    
    search_term = input("Enter search term (e.g., ES, NQ, NQ?5, NQ*): ")
    if not search_term:
        print(f"{Fore.RED}Search term cannot be empty{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    has_wildcards = '*' in search_term or '?' in search_term
    api_search_term = search_term
    if has_wildcards:
        api_search_term = re.split(r'[\*\?]', search_term)[0]
        if not api_search_term:
            api_search_term = search_term.replace('*', '').replace('?', '')
            if not api_search_term:
                api_search_term = 'A'
    
    exchange = input(f"Enter exchange (default: {current_exchange}): ")
    if exchange:
        current_exchange = exchange
    
    try:
        print(f"\nSearching for '{search_term}' on {current_exchange}...")
        try:
            results = await search_symbols_func(
                rithmic_client,
                api_search_term,
                instrument_type=InstrumentType.FUTURE,
                exchange=current_exchange
            )
        except Exception as e:
            print(f"{Fore.RED}Error searching for symbols: {e}{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return
        
        if not results:
            print(f"{Fore.YELLOW}No symbols found matching '{search_term}' on {current_exchange}{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return
        
        # Filter results if wildcards used
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
                print(f"{Fore.YELLOW}No symbols found matching wildcard pattern '{search_term}' on {current_exchange}{Style.RESET_ALL}")
                input("\nPress Enter to continue...")
                return
        
        print(f"\n{Fore.GREEN}Found {len(filtered_results)} symbols:{Style.RESET_ALL}")
        symbols = []
        full_symbols = []
        display_items = []
        
        for i, result in enumerate(filtered_results, 1):
            symbols.append(result.product_code)
            full_symbols.append(result.symbol)
            item = {
                'index': i,
                'symbol': result.symbol,
                'product_code': result.product_code,
                'name': result.symbol_name,
                'type': result.instrument_type,
                'expiration': result.expiration_date,
                'selected': False
            }
            display_items.append(item)
        
        selected_indices = await interactive_select_symbols(display_items)
        if not selected_indices:
            print(f"{Fore.YELLOW}No symbols selected{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return
        
        product_codes = [symbols[idx] for idx in selected_indices]
        current_symbols = [full_symbols[idx] for idx in selected_indices]
        
        print(f"\n{Fore.GREEN}Selected symbols: {', '.join(current_symbols)}{Style.RESET_ALL}")
        
        # Now check contracts for selected symbols
        print(f"\n{Fore.YELLOW}Checking Available Contracts...{Style.RESET_ALL}")
        available_contracts = {}
        
        for symbol in current_symbols:
            print(f"Checking contracts for {symbol}...")
            product_code = symbol
            match = re.match(r'^([A-Za-z]+)', symbol)
            if match:
                product_code = match.group(1)
            
            try:
                front_month_result = await get_front_month_contract(rithmic_client, product_code, current_exchange)
                front_month = front_month_result if front_month_result else "No front month contract found"
                
                contract_results = await search_symbols_func(
                    rithmic_client,
                    product_code,
                    instrument_type=InstrumentType.FUTURE,
                    exchange=current_exchange
                )
            except Exception as e:
                front_month = f"Error determining front month: {e}"
                contract_results = []
            
            if not contract_results:
                print(f"{Fore.YELLOW}Warning: No contracts found for {symbol}.{Style.RESET_ALL}")
                continue
            
            contracts = []
            for result in contract_results:
                if result.symbol == symbol:
                    contracts.append(result.symbol)
            
            if not contracts:
                print(f"{Fore.YELLOW}Warning: No exact match found for {symbol}.{Style.RESET_ALL}")
                continue
            
            contracts.sort()
            available_contracts[symbol] = contracts
            
            print(f"  Front month: {front_month}")
            print(f"  Contract: {symbol}")
            
            # Check data points in TimescaleDB
            if db_connected:
                try:
                    async with get_async_session() as session:
                        helper = TimescaleDBHelper(session)
                        latest_data = await helper.get_latest_data(symbol, current_exchange, limit=1)
                        
                        from sqlalchemy import text
                        result = await session.execute(
                            text("SELECT COUNT(*) FROM market_data_seconds WHERE symbol = :symbol AND exchange = :exchange"),
                            {'symbol': symbol, 'exchange': current_exchange}
                        )
                        second_count = result.scalar()
                        
                        result = await session.execute(
                            text("SELECT COUNT(*) FROM market_data_minutes WHERE symbol = :symbol AND exchange = :exchange"),
                            {'symbol': symbol, 'exchange': current_exchange}
                        )
                        minute_count = result.scalar()
                        
                        total_datapoints = second_count + minute_count
                        print(f"  Data points in TimescaleDB: {total_datapoints:,} total")
                        print(f"    - Second bars: {second_count:,}")
                        print(f"    - Minute bars: {minute_count:,}")
                        
                        if latest_data is not None and not latest_data.empty:
                            latest_timestamp = latest_data.iloc[0]['timestamp']
                            print(f"    - Latest data: {latest_timestamp}")
                except Exception as e:
                    print(f"  {Fore.YELLOW}Error checking TimescaleDB data: {e}{Style.RESET_ALL}")
            else:
                print(f"  {Fore.YELLOW}TimescaleDB not connected - cannot check data points{Style.RESET_ALL}")
            print()
        
        print(f"{Fore.GREEN}Symbol search and contract check completed{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error in symbol search and contract check: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def interactive_select_symbols(items):
    """Interactive symbol selection with arrow keys"""
    if not items:
        return []
    
    kb = KeyBindings()
    current_index = 0
    
    def get_formatted_list():
        result = []
        for i, item in enumerate(items):
            prefix = "→ " if i == current_index else "  "
            selected = "[X]" if item['selected'] else "[ ]"
            
            # Month code display
            month_code = ""
            month_name = ""
            symbol = item['symbol']
            if len(symbol) > 2:
                for char in symbol[2:]:
                    if char.isalpha():
                        month_map = {
                            'H': 'March', 'M': 'June', 'U': 'September', 'Z': 'December'
                        }
                        if char.upper() in month_map:
                            month_code = char.upper()
                            month_name = month_map[month_code]
                            month_display = f"{Fore.YELLOW}{month_name}{Style.RESET_ALL}"
                        else:
                            month_code = char.upper()
                            month_display = month_code
                        break
            
            line = f"{prefix}{selected} {item['index']}. Symbol: {symbol}"
            if month_code:
                line += f" (Month: {month_display})"
            line += f" | Product: {item['product_code']}"
            line += f" | Exp: {item['expiration']}"
            
            if i == current_index:
                line = f"{Fore.CYAN}{line}{Style.RESET_ALL}"
            elif item['selected']:
                line = f"{Fore.GREEN}{line}{Style.RESET_ALL}"
            
            result.append(line)
        return "\n".join(result)
    
    def print_selection_header():
        print("\033[H\033[J")  # Clear screen
        print(f"{Fore.YELLOW}Use arrow keys to navigate, Space to select/deselect, Enter to confirm{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Press 'a' to select all, 'n' to deselect all{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Month codes: H=March, M=June, U=September, Z=December{Style.RESET_ALL}")
    
    @kb.add(Keys.Up)
    def _(event):
        nonlocal current_index
        if current_index > 0:
            current_index -= 1
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add(Keys.Down)
    def _(event):
        nonlocal current_index
        if current_index < len(items) - 1:
            current_index += 1
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add(' ')
    def _(event):
        items[current_index]['selected'] = not items[current_index]['selected']
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add('a')
    def _(event):
        for item in items:
            item['selected'] = True
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add('n')
    def _(event):
        for item in items:
            item['selected'] = False
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add(Keys.Enter)
    def _(event):
        event.app.exit()
    
    session = PromptSession(key_bindings=kb)
    print_selection_header()
    print(get_formatted_list())
    await session.app.run_async()
    
    return [i for i, item in enumerate(items) if item['selected']]

async def get_front_month_contract(client, symbol, exchange):
    """Get front month contract for a symbol"""
    try:
        from search_symbols import search_symbols as search_symbols_func
        results = await search_symbols_func(
            client,
            symbol,
            instrument_type=InstrumentType.FUTURE,
            exchange=exchange
        )
        
        filtered_contracts = [r for r in results if hasattr(r, 'product_code') and r.product_code.startswith(symbol)]
        if filtered_contracts:
            sorted_contracts = sorted(filtered_contracts, key=lambda x: x.expiration_date if hasattr(x, 'expiration_date') else x.symbol)
            return sorted_contracts[0].symbol if sorted_contracts else None
        else:
            return None
    except Exception as e:
        logging.error(f"Error getting front month contract for {symbol}: {e}")
        return None

async def download_historical_data(cli_mode=False, days_to_download=7):
    """Download historical data and save to TimescaleDB"""
    global download_progress
    
    if not is_connected:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please test connections first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    if not db_connected:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: Not connected to TimescaleDB. Please test connections first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    if not available_contracts:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: No contracts available. Please search symbols first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    if not cli_mode:
        print_header()
    
    print(f"{Fore.YELLOW}Download Historical Data to TimescaleDB{Style.RESET_ALL}")
    
    days = days_to_download
    if not cli_mode:
        days_input = input("Enter number of days to download (default: 7): ")
        if days_input.strip():
            try:
                days = int(days_input)
            except ValueError:
                print(f"{Fore.RED}Invalid input. Using default of 7 days.{Style.RESET_ALL}")
                days = 7
    else:
        print(f"Downloading data for the last {days} days")
    
    print("\nBar Types:")
    print("1. Second bars")
    print("2. Minute bars") 
    print("3. Both")
    
    bar_choice = input("Enter choice (default: 1): ") if not cli_mode else "1"
    download_second_bars = bar_choice in ['1', '3', '']
    download_minute_bars = bar_choice in ['2', '3']
    
    if not download_second_bars and not download_minute_bars:
        print(f"{Fore.RED}Invalid choice. Defaulting to second bars.{Style.RESET_ALL}")
        download_second_bars = True
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    print(f"\nDownloading data from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"Bar types: {'Second bars' if download_second_bars else ''}{' and ' if download_second_bars and download_minute_bars else ''}{'Minute bars' if download_minute_bars else ''}")
    print(f"Target: TimescaleDB")
    
    download_progress = {symbol: 0.0 for symbol in available_contracts.keys()}
    total_contracts = sum(len(contracts) for contracts in available_contracts.values())
    contracts_processed = 0
    
    try:
        async with get_async_session() as session:
            helper = TimescaleDBHelper(session)
            
            for symbol, contracts in available_contracts.items():
                print(f"\nProcessing {symbol} contracts...")
                
                for contract in contracts:
                    print(f"  Processing {contract}...")
                    
                    if download_second_bars:
                        print_header()
                        print(f"  Downloading second bars for {contract}...")
                        
                        try:
                            all_second_bars = []
                            current_start = start_time
                            max_chunk_hours = 6
                            has_more_data = True
                            empty_chunks_in_a_row = 0
                            max_empty_chunks = 4
                            
                            def is_likely_market_hours(dt):
                                hour = dt.hour
                                weekday = dt.weekday()
                                # Basic market hours check (simplified)
                                if weekday == 5:  # Saturday
                                    return False
                                if weekday == 6 and hour >= 18:  # Sunday after 6 PM
                                    return True
                                if weekday == 4 and hour >= 17:  # Friday after 5 PM
                                    return False
                                if hour >= 17 and hour < 18:  # 5-6 PM gap
                                    return False
                                return True
                            
                            while has_more_data and empty_chunks_in_a_row < max_empty_chunks:
                                current_end = min(end_time, current_start + timedelta(hours=max_chunk_hours))
                                if current_end >= end_time:
                                    has_more_data = False
                                
                                if not is_likely_market_hours(current_start) and not is_likely_market_hours(current_end):
                                    print(f"    {Fore.YELLOW}Skipping chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')} (outside market hours){Style.RESET_ALL}")
                                    current_start = current_end
                                    continue
                                
                                print(f"    Requesting chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}")
                                
                                try:
                                    chunk_bars = await rithmic_client.get_historical_time_bars(
                                        contract,
                                        current_exchange,
                                        current_start,
                                        current_end,
                                        TimeBarType.SECOND_BAR,
                                        1
                                    )
                                except Exception as e:
                                    print(f"{Fore.RED}Error retrieving historical time bars: {e}{Style.RESET_ALL}")
                                    chunk_bars = []
                                
                                print(f"    {Fore.GREEN}Received {len(chunk_bars)} second bars for this chunk{Style.RESET_ALL}")
                                
                                if not chunk_bars:
                                    empty_chunks_in_a_row += 1
                                    print(f"    {Fore.YELLOW}Empty chunk ({empty_chunks_in_a_row}/{max_empty_chunks}){Style.RESET_ALL}")
                                else:
                                    empty_chunks_in_a_row = 0
                                
                                if len(chunk_bars) >= 9999:
                                    print(f"    {Fore.YELLOW}API limit reached (9999 data points), reducing chunk size{Style.RESET_ALL}")
                                    if max_chunk_hours > 1:
                                        max_chunk_hours = max_chunk_hours / 2
                                        print(f"    Reduced chunk size to {max_chunk_hours} hours")
                                        continue
                                
                                all_second_bars.extend(chunk_bars)
                                current_start = current_end
                            
                            print(f"  {Fore.GREEN}Total received: {len(all_second_bars)} second bars{Style.RESET_ALL}")
                            
                            # Save to TimescaleDB
                            if all_second_bars:
                                data_records = []
                                for bar in all_second_bars:
                                    record = {
                                        'timestamp': bar.get('bar_end_datetime', datetime.now()),
                                        'symbol': symbol,
                                        'contract': contract,
                                        'exchange': current_exchange,
                                        'exchange_code': 'XCME' if current_exchange == 'CME' else current_exchange,
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
                                
                                await helper.bulk_insert_market_data(data_records, 'market_data_seconds')
                                print(f"  {Fore.GREEN}Saved {len(data_records)} second bars to TimescaleDB{Style.RESET_ALL}")
                        
                        except Exception as e:
                            print(f"  {Fore.RED}Error downloading second bars: {e}{Style.RESET_ALL}")
                    
                    if download_minute_bars:
                        print_header()
                        print(f"  Downloading minute bars for {contract}...")
                        
                        try:
                            all_minute_bars = []
                            current_start = start_time
                            max_chunk_days = 2
                            has_more_data = True
                            empty_chunks_in_a_row = 0
                            max_empty_chunks = 3
                            
                            while has_more_data and empty_chunks_in_a_row < max_empty_chunks:
                                current_end = min(end_time, current_start + timedelta(days=max_chunk_days))
                                if current_end >= end_time:
                                    has_more_data = False
                                
                                print(f"    Requesting chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}")
                                
                                try:
                                    chunk_bars = await rithmic_client.get_historical_time_bars(
                                        contract,
                                        current_exchange,
                                        current_start,
                                        current_end,
                                        TimeBarType.MINUTE_BAR,
                                        1
                                    )
                                except Exception as e:
                                    print(f"{Fore.RED}Error retrieving historical time bars: {e}{Style.RESET_ALL}")
                                    chunk_bars = []
                                
                                print(f"    {Fore.GREEN}Received {len(chunk_bars)} minute bars for this chunk{Style.RESET_ALL}")
                                
                                if not chunk_bars:
                                    empty_chunks_in_a_row += 1
                                    print(f"    {Fore.YELLOW}Empty chunk ({empty_chunks_in_a_row}/{max_empty_chunks}){Style.RESET_ALL}")
                                else:
                                    empty_chunks_in_a_row = 0
                                
                                if len(chunk_bars) >= 9999:
                                    print(f"    {Fore.YELLOW}API limit reached (9999 data points), reducing chunk size{Style.RESET_ALL}")
                                    if max_chunk_days > 0.5:
                                        max_chunk_days = max_chunk_days / 2
                                        print(f"    Reduced chunk size to {max_chunk_days} days")
                                        continue
                                
                                all_minute_bars.extend(chunk_bars)
                                current_start = current_end
                            
                            print(f"  {Fore.GREEN}Total received: {len(all_minute_bars)} minute bars{Style.RESET_ALL}")
                            
                            # Save to TimescaleDB
                            if all_minute_bars:
                                data_records = []
                                for bar in all_minute_bars:
                                    record = {
                                        'timestamp': bar.get('bar_end_datetime', datetime.now()),
                                        'symbol': symbol,
                                        'contract': contract,
                                        'exchange': current_exchange,
                                        'exchange_code': 'XCME' if current_exchange == 'CME' else current_exchange,
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
                                
                                await helper.bulk_insert_market_data(data_records, 'market_data_minutes')
                                print(f"  {Fore.GREEN}Saved {len(data_records)} minute bars to TimescaleDB{Style.RESET_ALL}")
                        
                        except Exception as e:
                            print(f"  {Fore.RED}Error downloading minute bars: {e}{Style.RESET_ALL}")
                    
                    contracts_processed += 1
                    download_progress[symbol] = contracts_processed / total_contracts
                    print_header()
        
        print(f"\n{Fore.GREEN}Historical data download completed to TimescaleDB{Style.RESET_ALL}")
        
        # Display summary
        try:
            async with get_async_session() as session:
                from sqlalchemy import text
                
                # Count total records
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
                second_count = result.scalar()
                
                result = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
                minute_count = result.scalar()
                
                print(f"\n{Fore.CYAN}TimescaleDB Summary:{Style.RESET_ALL}")
                print(f"Total second bars in database: {second_count:,}")
                print(f"Total minute bars in database: {minute_count:,}")
                
                # Show latest data by symbol
                for symbol in current_symbols:
                    result = await session.execute(
                        text("SELECT COUNT(*), MAX(timestamp) FROM market_data_seconds WHERE symbol = :symbol"),
                        {'symbol': symbol}
                    )
                    row = result.fetchone()
                    if row and row[0] > 0:
                        print(f"{symbol}: {row[0]:,} records, latest: {row[1]}")
        
        except Exception as e:
            print(f"\n{Fore.YELLOW}Could not generate summary statistics: {e}{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"{Fore.RED}Error downloading historical data: {e}{Style.RESET_ALL}")
    
    if not cli_mode:
        input("\nPress Enter to continue...")

async def main_menu():
    """Main menu with combined options"""
    while True:
        print_header()
        print(f"{Fore.YELLOW}Main Menu{Style.RESET_ALL}")
        print("1. Test Connections (DB + Rithmic)")
        print("2. Search Symbols & Check Contracts")
        print("3. Download Historical Data")
        print("4. View TimescaleDB Data")
        print("5. Initialize/Setup Database")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            await test_connections()
        elif choice == '2':
            await search_and_check_symbols()
        elif choice == '3':
            await download_historical_data()
        elif choice == '4':
            await view_timescale_data()
        elif choice == '5':
            await initialize_database()
        elif choice == '0':
            if is_connected and rithmic_client:
                await disconnect_from_rithmic()
            print(f"{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
            time.sleep(1)

async def view_timescale_data():
    """View data stored in TimescaleDB"""
    if not db_connected:
        print_header()
        print(f"{Fore.RED}Error: Not connected to TimescaleDB. Please test connections first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    print_header()
    print(f"{Fore.YELLOW}TimescaleDB Data Viewer{Style.RESET_ALL}")
    
    try:
        async with get_async_session() as session:
            from sqlalchemy import text
            
            # Show table counts
            print(f"\n{Fore.CYAN}Table Summary:{Style.RESET_ALL}")
            
            result = await session.execute(text("SELECT COUNT(*) FROM market_data_seconds"))
            second_count = result.scalar()
            print(f"market_data_seconds: {second_count:,} records")
            
            result = await session.execute(text("SELECT COUNT(*) FROM market_data_minutes"))
            minute_count = result.scalar()
            print(f"market_data_minutes: {minute_count:,} records")
            
            # Show symbols in database
            print(f"\n{Fore.CYAN}Available Symbols:{Style.RESET_ALL}")
            result = await session.execute(text("""
                SELECT symbol, exchange, COUNT(*) as count, 
                       MIN(timestamp) as first_data, 
                       MAX(timestamp) as last_data
                FROM market_data_seconds 
                GROUP BY symbol, exchange 
                ORDER BY symbol, exchange
            """))
            
            symbols_data = result.fetchall()
            if symbols_data:
                for row in symbols_data:
                    print(f"{row[0]} ({row[1]}): {row[2]:,} records, {row[3]} to {row[4]}")
            else:
                print("No data found in market_data_seconds table")
            
            # Show recent data sample
            if second_count > 0:
                print(f"\n{Fore.CYAN}Recent Data Sample:{Style.RESET_ALL}")
                result = await session.execute(text("""
                    SELECT timestamp, symbol, contract, exchange, 
                           open, high, low, close, volume
                    FROM market_data_seconds 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """))
                
                recent_data = result.fetchall()
                for row in recent_data:
                    print(f"{row[0]} | {row[1]} {row[2]} | O:{row[4]} H:{row[5]} L:{row[6]} C:{row[7]} V:{row[8]}")
    
    except Exception as e:
        print(f"{Fore.RED}Error viewing TimescaleDB data: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def initialize_database():
    """Initialize TimescaleDB with proper schema"""
    print_header()
    print(f"{Fore.YELLOW}Initialize TimescaleDB{Style.RESET_ALL}")
    
    try:
        db_manager = get_database_manager()
        
        print("1. Testing connection...")
        connection_ok = await db_manager.test_connection()
        if not connection_ok:
            print(f"{Fore.RED}❌ Database connection failed{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return
        
        print(f"{Fore.GREEN}✅ Database connection successful{Style.RESET_ALL}")
        
        print("2. Initializing database extensions...")
        await db_manager.initialize_database()
        
        print("3. Creating hypertables...")
        await db_manager.create_hypertables()
        
        print("4. Setting up retention policies...")
        await db_manager.setup_retention_policies()
        
        print(f"\n{Fore.GREEN}✅ Database initialization completed successfully!{Style.RESET_ALL}")
        
        global db_connected
        db_connected = True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Database initialization failed: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def process_command_line_args(args):
    """Process command line arguments"""
    data_types = []
    if args.data_types:
        try:
            type_names = [t.strip().upper() for t in args.data_types.split(',')]
            for type_name in type_names:
                try:
                    if type_name == "HISTORY":
                        data_types.append("HISTORY")
                        print(f"Historical data access is available by default")
                    else:
                        try:
                            data_type = DataType[type_name]
                            data_types.append(data_type)
                            print(f"Enabling data type: {type_name}")
                        except KeyError:
                            print(f"Warning: {type_name} is not a valid DataType enum value")
                except (KeyError, AttributeError) as e:
                    print(f"{Fore.YELLOW}Warning: Unknown data type '{type_name}': {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Error parsing data types: {e}{Style.RESET_ALL}")
    
    if args.enable_history:
        if "HISTORY" not in data_types:
            data_types.append("HISTORY")
            print(f"{Fore.CYAN}Added HISTORY to enabled data types{Style.RESET_ALL}")
    
    if args.connect or args.test_connections:
        await test_connections(cli_mode=True)
        if not any(getattr(args, attr) for attr in vars(args) if attr not in ['connect', 'test_connections', 'data_types', 'enable_history']):
            await disconnect_from_rithmic()
            return
    
    if args.search_symbols:
        global current_exchange
        from search_symbols import search_symbols as search_symbols_func
        search_term = args.search_symbols
        print(f"\nSearching for '{search_term}' on {current_exchange}...")
        
        has_wildcards = '*' in search_term or '?' in search_term
        api_search_term = search_term
        if has_wildcards:
            api_search_term = re.split(r'[\*\?]', search_term)[0]
            if not api_search_term:
                api_search_term = search_term.replace('*', '').replace('?', '')
                if not api_search_term:
                    api_search_term = 'A'
        
        try:
            results = await search_symbols_func(
                rithmic_client,
                api_search_term,
                instrument_type=InstrumentType.FUTURE,
                exchange=current_exchange
            )
            
            if not results:
                print(f"{Fore.YELLOW}No symbols found matching '{search_term}' on {current_exchange}{Style.RESET_ALL}")
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
            
            print(f"\n{Fore.GREEN}Found {len(filtered_results)} symbols:{Style.RESET_ALL}")
            for i, result in enumerate(filtered_results, 1):
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
                                month_display = f"{Fore.YELLOW}{month_name}{Style.RESET_ALL}"
                            else:
                                month_code = char.upper()
                                month_display = month_code
                            break
                
                line = f"{i}. Symbol: {symbol}"
                if month_code:
                    line += f" (Month: {month_display})"
                line += f" | Product: {result.product_code}"
                line += f" | Exp: {result.expiration_date}"
                print(line)
        
        except Exception as e:
            print(f"{Fore.RED}Error searching symbols: {e}{Style.RESET_ALL}")
    
    if args.symbol:
        global current_symbols
        current_symbols = [args.symbol]
        print(f"\n{Fore.GREEN}Using symbol: {args.symbol}{Style.RESET_ALL}")
    
    if args.check_contracts:
        if not current_symbols:
            print(f"{Fore.RED}Error: No symbol specified. Use -s/--symbol to specify a symbol.{Style.RESET_ALL}")
        else:
            await search_and_check_symbols()
    
    if args.download_historical:
        if not current_symbols:
            print(f"{Fore.RED}Error: No symbol specified. Use -s/--symbol to specify a symbol.{Style.RESET_ALL}")
        else:
            days = 7
            if args.days:
                try:
                    days = int(args.days)
                except ValueError:
                    print(f"{Fore.YELLOW}Invalid days value. Using default of 7 days.{Style.RESET_ALL}")
            await download_historical_data(cli_mode=True, days_to_download=days)
    
    if is_connected and rithmic_client:
        await disconnect_from_rithmic()

if __name__ == "__main__":
    import argparse
    colorama.init()
    
    parser = argparse.ArgumentParser(description="Rithmic Data Admin Tool")
    parser.add_argument("-t", "--test-connections", action="store_true",
                        help="Test database and Rithmic connections")
    parser.add_argument("-S", "--search-symbols", type=str, metavar="PATTERN",
                        help="Search for symbols matching the pattern (e.g., 'NG?5', 'ES*')")
    parser.add_argument("-s", "--symbol", type=str, metavar="SYMBOL",
                        help="Use the specified symbol (e.g., 'NGM5')")
    parser.add_argument("-c", "--check-contracts", action="store_true",
                        help="Check contract existence and datapoints (requires -s/--symbol)")
    parser.add_argument("-d", "--download-historical", action="store_true",
                        help="Download historical data (requires -s/--symbol)")
    parser.add_argument("--days", type=str, metavar="DAYS",
                        help="Number of days to download (default: 7, used with -d/--download-historical)")
    parser.add_argument("--data-types", type=str, metavar="TYPES",
                        help="Comma-separated list of data types to enable (e.g., 'HISTORY,MARKET_DATA')")
    parser.add_argument("--connect", action="store_true",
                        help="Connect to Rithmic (can be used with --data-types)")
    parser.add_argument("--enable-history", action="store_true",
                        help="Enable history data type for historical data retrieval")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        try:
            asyncio.run(main_menu())
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Unhandled exception: {e}{Style.RESET_ALL}")
    else:
        try:
            asyncio.run(process_command_line_args(args))
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")
        except Exception as e:
            error_msg = f"Unhandled exception: {e}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            logger.exception(error_msg)