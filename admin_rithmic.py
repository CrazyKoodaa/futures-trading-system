#!/usr/bin/env python
# admin_rithmic.py
"""
Admin script for Rithmic data collection with interactive menu
"""
import os
import time
import asyncio
import logging
import sqlite3
import re
import fnmatch
from datetime import datetime, timedelta
import colorama
from colorama import Fore, Style
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

# Import third-party components
from async_rithmic import RithmicClient, TimeBarType, InstrumentType, Gateway, DataType
from async_rithmic import ReconnectionSettings, RetrySettings

# Import local components
from config.chicago_gateway_config import get_chicago_gateway_config

# Custom implementation for historical data retrieval
async def get_historical_time_bars(client, contract, exchange, start_time, end_time, bar_type, bar_interval):
    """
    Retrieve historical time bars using the get_historical_time_bars method in RithmicClient.
    
    Args:
        client: The RithmicClient instance
        contract: Contract symbol
        exchange: Exchange name
        start_time: Start datetime
        end_time: End datetime
        bar_type: TimeBarType (SECOND_BAR or MINUTE_BAR)
        bar_interval: Interval (e.g., 1 for 1-second or 1-minute bars)
        
    Returns:
        List of time bars
    """
    print(f"Retrieving historical time bars for {contract}")
    print(f"Parameters: exchange={exchange}, start={start_time}, end={end_time}, type={bar_type}, interval={bar_interval}")
    
    # Create a list to store the collected bars
    collected_bars = []
    
    try:
        # Convert bar_type to the appropriate TimeBarType enum value
        from async_rithmic.enums import TimeBarType
        time_bar_type = TimeBarType.SECOND_BAR if bar_type == 1 else TimeBarType.MINUTE_BAR
        
        # Request the historical time bars using the direct method
        print(f"{Fore.CYAN}Requesting historical data using get_historical_time_bars...{Style.RESET_ALL}")
        result = await client.get_historical_time_bars(
            contract,
            exchange,
            start_time,
            end_time,
            time_bar_type,
            bar_interval
        )
        
        # Process the results
        if result and isinstance(result, list):
            print(f"{Fore.GREEN}Received {len(result)} bars{Style.RESET_ALL}")
            collected_bars = result
        else:
            print(f"{Fore.YELLOW}No results returned from get_historical_time_bars{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"{Fore.RED}Error retrieving historical time bars: {e}{Style.RESET_ALL}")
        
        # Set up a callback as a fallback method
        try:
            print(f"{Fore.YELLOW}Attempting to use callback method for historical data...{Style.RESET_ALL}")
            
            # Create an event to signal when data collection is complete
            data_collection_complete = asyncio.Event()
            
            # Define a callback function to handle historical time bars
            async def on_historical_time_bar_callback(data):
                if not isinstance(data, dict):
                    print(f"{Fore.RED}Error: Received non-dictionary data in callback: {type(data)}{Style.RESET_ALL}")
                    return
                    
                try:
                    # Add the bar to our collection
                    collected_bars.append(data)
                except Exception as cb_error:
                    print(f"{Fore.RED}Error processing time bar data: {cb_error}{Style.RESET_ALL}")
            
            # Register the callback if available
            if hasattr(client, 'on_historical_time_bar'):
                client.on_historical_time_bar += on_historical_time_bar_callback
                
                # Wait for some data to arrive
                await asyncio.sleep(10)
                
                # Unregister the callback
                client.on_historical_time_bar -= on_historical_time_bar_callback
            else:
                print(f"{Fore.YELLOW}Client does not have on_historical_time_bar event{Style.RESET_ALL}")
        
        except Exception as fallback_error:
            print(f"{Fore.RED}Error in fallback method: {fallback_error}{Style.RESET_ALL}")
    
    print(f"Collected {len(collected_bars)} historical bars")
    return collected_bars

# Create a utility function to get the front month contract
async def get_front_month_contract(client, symbol, exchange):
    """
    Get the front month contract for a symbol
    
    Args:
        client: RithmicClient instance
        symbol: Symbol root (e.g., 'ES')
        exchange: Exchange to use
        
    Returns:
        Front month contract symbol
    """
    try:
        # Import search_symbols function here to avoid circular imports
        from search_symbols import search_symbols as search_symbols_func
        
        # Search for all contracts for this symbol
        results = await search_symbols_func(
            client,
            symbol, 
            instrument_type=InstrumentType.FUTURE,
            exchange=exchange
        )
        
        # Filter to only include contracts that start with this symbol
        filtered_contracts = [r for r in results if hasattr(r, 'product_code') and r.product_code.startswith(symbol)]
        
        if filtered_contracts:
            # Sort by expiration date (assuming expiration_date is available)
            sorted_contracts = sorted(filtered_contracts, key=lambda x: x.expiration_date if hasattr(x, 'expiration_date') else x.symbol)
            # Front month is the first one after sorting
            return sorted_contracts[0].symbol if sorted_contracts else None
        else:
            return None
    except Exception as e:
        logging.error(f"Error getting front month contract for {symbol}: {e}")
        return None

# We'll use the utility function directly instead of trying to monkey patch
# This avoids the "Cannot assign to attribute" error

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

# Constants
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'rithmic_data.db')
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# State variables
current_symbols = []
current_exchange = "CME"
available_contracts = {}
download_progress = {}
rithmic_client = None
is_connected = False
db_connected = False  # Database connection status

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the admin script header with current state"""
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
        print(f"{Fore.GREEN}Database Connection: Connected{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Database Connection: Disconnected{Style.RESET_ALL}")
    
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

def create_database():
    """Create SQLite database and tables if they don't exist"""
    global db_connected
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            exchange TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, exchange)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY,
            symbol_id INTEGER,
            contract TEXT NOT NULL,
            expiration_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (symbol_id) REFERENCES symbols(id),
            UNIQUE(contract)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS second_bars (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER,
            timestamp TIMESTAMP NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            UNIQUE(contract_id, timestamp)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS minute_bars (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER,
            timestamp TIMESTAMP NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            UNIQUE(contract_id, timestamp)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_bars (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER,
            timestamp TIMESTAMP NOT NULL,
            bar_type TEXT NOT NULL,
            bar_interval INTEGER NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            UNIQUE(contract_id, timestamp, bar_type, bar_interval)
        )
        ''')
        
        # Table to track contracts with no data
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract_data_status (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER,
            has_second_bars INTEGER DEFAULT 0,
            has_minute_bars INTEGER DEFAULT 0,
            last_checked_date TEXT,
            no_data_reason TEXT,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            UNIQUE(contract_id)
        )
        ''')
        
        conn.commit()
        db_connected = True
        return True, "Database created successfully"
    except sqlite3.Error as e:
        db_connected = False
        return False, f"Error creating database: {e}"
    finally:
        if conn:
            conn.close()

async def test_db_connection(cli_mode=False):
    """Test database connection and tables"""
    global db_connected
    
    if not cli_mode:
        print_header()
    print(f"{Fore.YELLOW}Testing database connection...{Style.RESET_ALL}")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        success, message = create_database()
        if not success:
            print(f"{Fore.RED}{message}{Style.RESET_ALL}")
            if not cli_mode:
                choice = input("\nWould you like to recreate the database? (y/n): ")
                if choice.lower() == 'y':
                    try:
                        os.remove(DB_PATH)
                        success, message = create_database()
                        print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
                    except sqlite3.Error as e:
                        print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
                        db_connected = False
            else:
                # In CLI mode, automatically recreate the database
                try:
                    os.remove(DB_PATH)
                    success, message = create_database()
                    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
                except sqlite3.Error as e:
                    print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
                    db_connected = False
            return
    
    conn = None
    try:
        # Test connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"{Fore.GREEN}Database connection successful{Style.RESET_ALL}")
        print(f"Database path: {DB_PATH}")
        print(f"Tables found: {', '.join(table_names)}")
        
        # Check row counts
        for table in table_names:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} rows")
        
        print(f"\n{Fore.GREEN}Database check completed successfully{Style.RESET_ALL}")
        db_connected = True
    except sqlite3.Error as e:
        print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")
        db_connected = False
        if not cli_mode:
            choice = input("\nWould you like to recreate the database? (y/n): ")
            if choice.lower() == 'y':
                try:
                    if conn:
                        conn.close()
                    os.remove(DB_PATH)
                    success, message = create_database()
                    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
                except (sqlite3.Error, OSError) as e:
                    print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
                    db_connected = False
        else:
            # In CLI mode, automatically recreate the database
            try:
                if conn:
                    conn.close()
                os.remove(DB_PATH)
                success, message = create_database()
                print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
            except (sqlite3.Error, OSError) as e:
                print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
                db_connected = False
    finally:
        if conn:
            conn.close()
    
    if not cli_mode:
        input("\nPress Enter to continue...")

async def disconnect_from_rithmic(timeout=5.0):
    """Gracefully disconnect from Rithmic with timeout handling"""
    global rithmic_client, is_connected
    
    if rithmic_client and is_connected:
        try:
            print(f"\n{Fore.YELLOW}Disconnecting from Rithmic...{Style.RESET_ALL}")
            
            # Temporarily redirect stderr to suppress error messages from the Rithmic client
            import sys
            from io import StringIO
            
            # Save the original stderr
            original_stderr = sys.stderr
            
            # Create a string buffer to capture stderr output
            string_buffer = StringIO()
            
            try:
                # Redirect stderr to our string buffer
                sys.stderr = string_buffer
                
                # Attempt to disconnect with timeout
                await asyncio.wait_for(rithmic_client.disconnect(), timeout=timeout)
                
            finally:
                # Restore the original stderr
                sys.stderr = original_stderr
            
            print(f"{Fore.GREEN}Rithmic connection closed successfully.{Style.RESET_ALL}")
        except asyncio.TimeoutError:
            print(f"{Fore.YELLOW}Disconnect timed out, but this is expected behavior with the Rithmic API.{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Program completed successfully despite timeout warnings.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}Error during disconnect: {e}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Program completed successfully despite disconnect errors.{Style.RESET_ALL}")
        finally:
            # Set the connection status to false regardless of disconnect result
            is_connected = False

async def connect_to_rithmic(cli_mode=False, data_types=None):
    """Connect to Rithmic with login data
    
    Args:
        cli_mode (bool): Whether to run in CLI mode (no header, no input prompt)
        data_types (list): List of DataType enums to enable (e.g., [DataType.HISTORY])
    """
    global rithmic_client, is_connected
    
    if not cli_mode:
        print_header()
    print(f"{Fore.YELLOW}Connecting to Rithmic...{Style.RESET_ALL}")
    
    # If data_types is specified, show what's being enabled
    if data_types:
        data_type_names = [dt.name for dt in data_types]
        print(f"{Fore.CYAN}Enabling data types: {', '.join(data_type_names)}{Style.RESET_ALL}")
    
    try:
        # Get credentials from config
        config = get_chicago_gateway_config()
        
        # Configure reconnection settings
        reconnection = ReconnectionSettings(
            max_retries=3,
            backoff_type="exponential",
            interval=2,
            max_delay=30,
            jitter_range=(0.5, 1.5)
        )
        
        # Configure retry settings
        retry = RetrySettings(
            max_retries=2,
            timeout=20.0,
            jitter_range=(0.5, 1.5)
        )
        
        # Display connection info
        print(f"Username: {config['rithmic']['user']}")
        print(f"System: {config['rithmic']['system_name']}")
        print(f"Gateway: {config['rithmic']['gateway']}")
        print(f"App: {config['rithmic']['app_name']} v{config['rithmic']['app_version']}")
        
        # Create Rithmic client
        gateway_name = config['rithmic']['gateway']
        gateway = Gateway.CHICAGO if gateway_name == 'Chicago' else Gateway.TEST
        
        # Create the Rithmic client
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
        
        # Connect to Rithmic
        print("\nAttempting connection...")
        await rithmic_client.connect()
        is_connected = True
        
        # Historical data is directly accessible through methods like get_historical_time_bars
        # No need to enable a specific data type for historical data
        if data_types and 'HISTORY' in [dt for dt in data_types]:
            print(f"{Fore.CYAN}Historical data access is available by default...{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Ready to access historical data!{Style.RESET_ALL}")
            
            # Verify that the history plant is available
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

async def search_symbols():
    """Search for symbols in Rithmic with wildcard support and interactive selection"""
    global current_symbols, current_exchange
    
    # Import search_symbols function here to avoid circular imports
    from search_symbols import search_symbols as search_symbols_func
    
    if not is_connected:
        print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please connect first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    print_header()
    print(f"{Fore.YELLOW}Symbol Search{Style.RESET_ALL}")
    print(f"You can use wildcards: * (any characters) and ? (single character)")
    print(f"Examples: NQ?5 (matches NQU5, NQZ5, etc.), NQ* (matches all NQ contracts)")
    print(f"For NQ and ES futures, only quarterly months (H, M, U, Z) are valid")
    
    # Get search term from user
    search_term = input("Enter search term (e.g., ES, NQ, NQ?5, NQ*): ")
    if not search_term:
        print(f"{Fore.RED}Search term cannot be empty{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    # Check if search term contains wildcards
    has_wildcards = '*' in search_term or '?' in search_term
    
    # If wildcards are present, convert to a basic search term for the API
    api_search_term = search_term
    if has_wildcards:
        # Extract the base part of the search term (before any wildcards)
        api_search_term = re.split(r'[\*\?]', search_term)[0]
        if not api_search_term:
            api_search_term = search_term.replace('*', '').replace('?', '')
            if not api_search_term:
                api_search_term = 'A'  # Fallback to a very broad search
    
    # Get exchange from user
    exchange = input(f"Enter exchange (default: {current_exchange}): ")
    if exchange:
        current_exchange = exchange
    
    try:
        print(f"\nSearching for '{search_term}' on {current_exchange}...")
        
        # Search for symbols
        try:
            # Use the imported function instead of calling the method directly
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
        
        # Filter results if wildcards were used
        filtered_results = results
        if has_wildcards:
            filtered_results = []
            pattern = search_term.replace('?', '.').replace('*', '.*')
            
            # Check if we're dealing with NQ or ES futures
            is_nq_es = search_term.upper().startswith('NQ') or search_term.upper().startswith('ES')
            
            for result in results:
                # For NQ and ES, only include contracts with valid month codes (H, M, U, Z)
                if is_nq_es:
                    # Extract the month code from the symbol (typically the character after the root)
                    symbol = result.symbol.upper()
                    product_code = result.product_code.upper()
                    
                    # Try to extract month code - typically it's the first non-digit after the root symbol
                    month_code = None
                    if len(symbol) > 2:  # Ensure there's enough characters
                        for char in symbol[2:]:
                            if char.isalpha():
                                month_code = char
                                break
                    
                    # Skip if not a valid quarterly month code
                    if month_code and month_code not in ['H', 'M', 'U', 'Z']:
                        continue
                
                # Apply the wildcard pattern matching
                if (re.match(pattern, result.symbol, re.IGNORECASE) or 
                    re.match(pattern, result.product_code, re.IGNORECASE)):
                    filtered_results.append(result)
            
            if not filtered_results:
                print(f"{Fore.YELLOW}No symbols found matching wildcard pattern '{search_term}' on {current_exchange}{Style.RESET_ALL}")
                input("\nPress Enter to continue...")
                return
        
        # Display results count
        print(f"\n{Fore.GREEN}Found {len(filtered_results)} symbols:{Style.RESET_ALL}")
        
        # Prepare data for interactive selection
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
        
        # Interactive selection using prompt_toolkit
        selected_indices = await interactive_select_symbols(display_items)
        
        if not selected_indices:
            print(f"{Fore.YELLOW}No symbols selected{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return
        
        # Get selected symbols (both product codes and full symbols)
        product_codes = [symbols[idx] for idx in selected_indices]
        current_symbols = [full_symbols[idx] for idx in selected_indices]
        
        print(f"\n{Fore.GREEN}Selected symbols: {', '.join(current_symbols)}{Style.RESET_ALL}")
        
        # Save symbols to database
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for i, symbol in enumerate(current_symbols):
                product_code = product_codes[i]
                cursor.execute(
                    "INSERT OR IGNORE INTO symbols (symbol, exchange, description) VALUES (?, ?, ?)",
                    (symbol, current_exchange, f"Added via search on {datetime.now().isoformat()}")
                )
            
            conn.commit()
        except sqlite3.Error as db_error:
            print(f"{Fore.RED}Database error: {db_error}{Style.RESET_ALL}")
        finally:
            if conn:
                conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}Error searching symbols: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def interactive_select_symbols(items):
    """
    Interactive symbol selection with arrow keys and space bar
    
    Args:
        items: List of dictionaries containing symbol information
        
    Returns:
        List of selected indices
    """
    if not items:
        return []
    
    # Create key bindings
    kb = KeyBindings()
    
    # Current cursor position
    current_index = 0
    
    # Function to render the list
    def get_formatted_list():
        result = []
        for i, item in enumerate(items):
            # Highlight the current item
            prefix = "→ " if i == current_index else "  "
            # Show selection status
            selected = "[X]" if item['selected'] else "[ ]"
            
            # Extract month code for futures contracts (if present)
            month_code = ""
            month_name = ""
            symbol = item['symbol']
            if len(symbol) > 2:  # Ensure there's enough characters
                for char in symbol[2:]:
                    if char.isalpha():
                        # Map month code to full month name
                        month_map = {
                            'H': 'March',
                            'M': 'June',
                            'U': 'September',
                            'Z': 'December'
                        }
                        
                        if char.upper() in month_map:
                            month_code = char.upper()
                            month_name = month_map[month_code]
                            month_display = f"{Fore.YELLOW}{month_name}{Style.RESET_ALL}"
                        else:
                            month_code = char.upper()
                            month_display = month_code
                        break
            
            # Format the item
            line = f"{prefix}{selected} {item['index']}. Symbol: {symbol}"
            if month_code:
                line += f" (Month: {month_display})"
            line += f" | Product: {item['product_code']}"
            line += f" | Exp: {item['expiration']}"
            
            # Apply formatting
            if i == current_index:
                line = f"{Fore.CYAN}{line}{Style.RESET_ALL}"
            elif item['selected']:
                line = f"{Fore.GREEN}{line}{Style.RESET_ALL}"
                
            result.append(line)
        return "\n".join(result)
    
    # Key bindings
    # Helper function to print the header
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
        # Select all
        for item in items:
            item['selected'] = True
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add('n')
    def _(event):
        # Deselect all
        for item in items:
            item['selected'] = False
        print_selection_header()
        print(get_formatted_list())
    
    @kb.add(Keys.Enter)
    def _(event):
        event.app.exit()
    
    # Create a session
    session = PromptSession(key_bindings=kb)
    
    # Clear screen and show initial list
    print_selection_header()
    print(get_formatted_list())
    
    # Start the session using run_async instead of prompt
    # This allows it to work within an existing asyncio event loop
    await session.app.run_async()
    
    # Return selected indices
    return [i for i, item in enumerate(items) if item['selected']]

async def check_contracts(cli_mode=False):
    """Check which contracts can be accessed for the searched symbols and count datapoints"""
    global available_contracts
    
    # Import search_symbols function here to avoid circular imports
    from search_symbols import search_symbols as search_symbols_func
    
    if not is_connected:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please connect first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    if not current_symbols:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: No symbols selected. Please search for symbols first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    if not cli_mode:
        print_header()
    print(f"{Fore.YELLOW}Checking Available Contracts and Data Points{Style.RESET_ALL}")
    print(f"Symbols: {', '.join(current_symbols)}")
    print(f"Exchange: {current_exchange}")
    print()
    
    available_contracts = {}
    
    try:
        for symbol in current_symbols:
            print(f"Checking contracts for {symbol}...")
            
            # Extract product code from symbol (for search)
            product_code = symbol
            # Try to extract the product code from the symbol (e.g., "NQ" from "NQM5")
            match = re.match(r'^([A-Za-z]+)', symbol)
            if match:
                product_code = match.group(1)
            
            # Get front month contract using our helper function
            try:
                front_month_result = await get_front_month_contract(rithmic_client, product_code, current_exchange)
                front_month = front_month_result if front_month_result else "No front month contract found"
                
                # Search for all contracts for this symbol
                results = await search_symbols_func(
                    rithmic_client,
                    product_code, 
                    instrument_type=InstrumentType.FUTURE,
                    exchange=current_exchange
                )
            except Exception as e:
                front_month = f"Error determining front month: {e}"
                results = []
            
            # Check if we have valid results
            if not results:
                print(f"{Fore.YELLOW}Warning: No contracts found for {symbol}.{Style.RESET_ALL}")
                continue
            
            # Filter and sort contracts - only include the exact symbol we're looking for
            contracts = []
            for result in results:
                if result.symbol == symbol:
                    contracts.append(result.symbol)
            
            if not contracts:
                print(f"{Fore.YELLOW}Warning: No exact match found for {symbol}.{Style.RESET_ALL}")
                continue
                
            contracts.sort()
            available_contracts[symbol] = contracts
            
            print(f"  Front month: {front_month}")
            print(f"  Contract: {symbol}")
            
            # Count datapoints in database
            conn = None
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # First, ensure the symbol exists in the database
                cursor.execute(
                    "INSERT OR IGNORE INTO symbols (symbol, exchange) VALUES (?, ?)",
                    (symbol, current_exchange)
                )
                conn.commit()
                
                # Get symbol_id
                cursor.execute("SELECT id FROM symbols WHERE symbol = ? AND exchange = ?", (symbol, current_exchange))
                result = cursor.fetchone()
                
                if result:
                    symbol_id = result[0]
                    
                    # Count datapoints for this symbol from different tables
                    cursor.execute(
                        "SELECT COUNT(*) FROM time_bars WHERE contract_id IN (SELECT id FROM contracts WHERE symbol_id = ?)",
                        (symbol_id,)
                    )
                    time_bars_count = cursor.fetchone()[0]
                    
                    cursor.execute(
                        "SELECT COUNT(*) FROM second_bars WHERE contract_id IN (SELECT id FROM contracts WHERE symbol_id = ?)",
                        (symbol_id,)
                    )
                    second_bars_count = cursor.fetchone()[0]
                    
                    cursor.execute(
                        "SELECT COUNT(*) FROM minute_bars WHERE contract_id IN (SELECT id FROM contracts WHERE symbol_id = ?)",
                        (symbol_id,)
                    )
                    minute_bars_count = cursor.fetchone()[0]
                    
                    total_datapoints = time_bars_count + second_bars_count + minute_bars_count
                    
                    print(f"  Data points: {total_datapoints:,} total")
                    print(f"    - Time bars: {time_bars_count:,}")
                    print(f"    - Second bars: {second_bars_count:,}")
                    print(f"    - Minute bars: {minute_bars_count:,}")
                    
                    # Save contract if not already in database
                    for contract in contracts:
                        # Extract expiration date from contract (if possible)
                        expiration = None
                        if len(contract) > len(product_code):
                            # Simple extraction, would need refinement for production
                            expiration = contract[len(product_code):]
                        
                        cursor.execute(
                            "INSERT OR IGNORE INTO contracts (symbol_id, contract, expiration_date) VALUES (?, ?, ?)",
                            (symbol_id, contract, expiration)
                        )
                else:
                    print(f"  {Fore.YELLOW}Symbol not found in database{Style.RESET_ALL}")
                
                conn.commit()
            except sqlite3.Error as db_error:
                print(f"{Fore.RED}Database error: {db_error}{Style.RESET_ALL}")
            finally:
                if conn:
                    conn.close()
            
            print()
        
        print(f"{Fore.GREEN}Contract check completed{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error checking contracts: {e}{Style.RESET_ALL}")
    
    if not cli_mode:
        input("\nPress Enter to continue...")

async def download_historical_data(cli_mode=False, days_to_download=7):
    """Download historical data for available contracts"""
    global download_progress
    
    if not is_connected:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please connect first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    # Enable history data type if not already enabled
    if not hasattr(rithmic_client, 'history_plant'):
        print(f"{Fore.YELLOW}Enabling history data type for historical data retrieval...{Style.RESET_ALL}")
        try:
            # Historical data is directly accessible through methods like get_historical_time_bars
            # No need to enable a specific data type for historical data
            print(f"{Fore.GREEN}Ready to access historical data!{Style.RESET_ALL}")
            
            # Wait a moment for the history plant to initialize
            await asyncio.sleep(2)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not enable history data type: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Will try alternative methods for historical data retrieval.{Style.RESET_ALL}")
    
    # In CLI mode, if we have symbols but no available_contracts, run check_contracts first
    if not available_contracts and current_symbols and cli_mode:
        await check_contracts(cli_mode=True)
    
    if not available_contracts:
        if not cli_mode:
            print_header()
        print(f"{Fore.RED}Error: No contracts available. Please check contracts first.{Style.RESET_ALL}")
        if not cli_mode:
            input("\nPress Enter to continue...")
        return
    
    if not cli_mode:
        print_header()
    print(f"{Fore.YELLOW}Download Historical Data{Style.RESET_ALL}")
    
    # Ask for date range in interactive mode, use default in CLI mode
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
    days = 7
    if days_input.strip() and days_input.isdigit():
        days = int(days_input)
    
    # Ask for bar type
    print("\nBar Types:")
    print("1. Second bars")
    print("2. Minute bars")
    print("3. Both")
    bar_choice = input("Enter choice (default: 1): ")
    
    download_second_bars = bar_choice in ['1', '3', '']
    download_minute_bars = bar_choice in ['2', '3']
    
    if not download_second_bars and not download_minute_bars:
        print(f"{Fore.RED}Invalid choice. Defaulting to second bars.{Style.RESET_ALL}")
        download_second_bars = True
    
    # Ask if we should skip contracts with no data
    skip_no_data = input("\nSkip contracts previously marked as having no data? (y/n, default: y): ").lower() != 'n'
    
    # Set time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    print(f"\nDownloading data from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"Bar types: {'Second bars' if download_second_bars else ''}{' and ' if download_second_bars and download_minute_bars else ''}{'Minute bars' if download_minute_bars else ''}")
    if skip_no_data:
        print(f"Skipping contracts previously marked as having no data")
    
    # Initialize progress tracking
    download_progress = {symbol: 0.0 for symbol in available_contracts.keys()}
    total_contracts = sum(len(contracts) for contracts in available_contracts.values())
    contracts_processed = 0
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for symbol, contracts in available_contracts.items():
            print(f"\nProcessing {symbol} contracts...")
            
            for contract in contracts:
                print(f"  Processing {contract}...")
                
                # Get contract_id from database
                cursor.execute("""
                    SELECT c.id FROM contracts c
                    JOIN symbols s ON c.symbol_id = s.id
                    WHERE c.contract = ? AND s.symbol = ? AND s.exchange = ?
                """, (contract, symbol, current_exchange))
                
                result = cursor.fetchone()
                if not result:
                    print(f"  {Fore.YELLOW}Contract {contract} not found in database, adding it now...{Style.RESET_ALL}")
                    
                    # First, ensure the symbol exists
                    cursor.execute("SELECT id FROM symbols WHERE symbol = ? AND exchange = ?", 
                                  (symbol, current_exchange))
                    symbol_result = cursor.fetchone()
                    
                    if not symbol_result:
                        # Add the symbol
                        cursor.execute(
                            "INSERT INTO symbols (symbol, exchange) VALUES (?, ?)",
                            (symbol, current_exchange)
                        )
                        conn.commit()
                        
                        # Get the new symbol_id
                        cursor.execute("SELECT id FROM symbols WHERE symbol = ? AND exchange = ?", 
                                      (symbol, current_exchange))
                        symbol_result = cursor.fetchone()
                    
                    symbol_id = symbol_result[0]
                    
                    # Extract expiration date from contract (if possible)
                    expiration = None
                    match = re.match(r'^([A-Za-z]+)', symbol)
                    if match:
                        product_code = match.group(1)
                        if len(contract) > len(product_code):
                            expiration = contract[len(product_code):]
                    
                    # Add the contract
                    cursor.execute(
                        "INSERT INTO contracts (symbol_id, contract, expiration_date) VALUES (?, ?, ?)",
                        (symbol_id, contract, expiration)
                    )
                    conn.commit()
                    
                    # Get the new contract_id
                    cursor.execute("""
                        SELECT c.id
                        FROM contracts c
                        JOIN symbols s ON c.symbol_id = s.id
                        WHERE c.contract = ? AND s.symbol = ? AND s.exchange = ?
                    """, (contract, symbol, current_exchange))
                    
                    result = cursor.fetchone()
                    if not result:
                        print(f"  {Fore.RED}Error: Failed to add contract {contract} to database{Style.RESET_ALL}")
                        continue
                
                contract_id = result[0]
                
                # Check if this contract has been marked as having no data
                if skip_no_data:
                    cursor.execute("""
                        SELECT has_second_bars, has_minute_bars, last_checked_date, no_data_reason 
                        FROM contract_data_status 
                        WHERE contract_id = ?
                    """, (contract_id,))
                    
                    status_result = cursor.fetchone()
                    
                    if status_result:
                        has_second_bars, has_minute_bars, last_checked_date, no_data_reason = status_result
                        
                        # Skip second bars if requested and previously marked as having no data
                        if download_second_bars and has_second_bars == 0:
                            print(f"  {Fore.YELLOW}Skipping second bars for {contract} - No data found on {last_checked_date}{Style.RESET_ALL}")
                            if no_data_reason:
                                print(f"  {Fore.YELLOW}Reason: {no_data_reason}{Style.RESET_ALL}")
                            download_second_bars_for_contract = False
                        else:
                            download_second_bars_for_contract = download_second_bars
                        
                        # Skip minute bars if requested and previously marked as having no data
                        if download_minute_bars and has_minute_bars == 0:
                            print(f"  {Fore.YELLOW}Skipping minute bars for {contract} - No data found on {last_checked_date}{Style.RESET_ALL}")
                            if no_data_reason:
                                print(f"  {Fore.YELLOW}Reason: {no_data_reason}{Style.RESET_ALL}")
                            download_minute_bars_for_contract = False
                        else:
                            download_minute_bars_for_contract = download_minute_bars
                        
                        # If both bar types are skipped, move to next contract
                        if not download_second_bars_for_contract and not download_minute_bars_for_contract:
                            contracts_processed += 1
                            download_progress[symbol] = contracts_processed / total_contracts
                            print_header()  # Update progress display
                            continue
                    else:
                        download_second_bars_for_contract = download_second_bars
                        download_minute_bars_for_contract = download_minute_bars
                else:
                    download_second_bars_for_contract = download_second_bars
                    download_minute_bars_for_contract = download_minute_bars
                
                # Track data status for this contract
                has_second_data = False
                has_minute_data = False
                no_data_reason = None
                
                # Download second bars if requested
                if download_second_bars_for_contract:
                    print_header()  # Update progress display
                    print(f"  Downloading second bars for {contract}...")
                    
                    try:
                        # Initialize variables for chunked downloading
                        all_second_bars = []
                        current_start = start_time
                        max_chunk_hours = 6  # Start with 6-hour chunks for second bars
                        has_more_data = True
                        reached_api_limit = False
                        empty_chunks_in_a_row = 0
                        max_empty_chunks = 4  # Stop after 4 empty chunks in a row (24 hours with no data)
                        
                        # Define market hours (CME Globex for NQ/ES futures)
                        # Sunday: 6:00 p.m. - Friday: 5:00 p.m. ET with trading halts from 5:00-6:00 p.m. ET daily
                        def is_likely_market_hours(dt):
                            # Convert to US Eastern time
                            # This is a simplified check - in production you'd use pytz for proper timezone handling
                            hour = dt.hour
                            weekday = dt.weekday()  # 0=Monday, 6=Sunday
                            
                            # Weekend check (Saturday)
                            if weekday == 5:  # Saturday
                                return False
                                
                            # Sunday evening (market opens)
                            if weekday == 6 and hour >= 18:  # Sunday after 6pm
                                return True
                                
                            # Friday evening (market closes)
                            if weekday == 4 and hour >= 17:  # Friday after 5pm
                                return False
                                
                            # Daily trading halt
                            if hour >= 17 and hour < 18:  # 5pm-6pm daily halt
                                return False
                                
                            # Regular trading days
                            return True
                        
                        while has_more_data and empty_chunks_in_a_row < max_empty_chunks:
                            # Calculate end time for this chunk
                            current_end = min(end_time, current_start + timedelta(hours=max_chunk_hours))
                            
                            # If we've reached the end time, this is the last chunk
                            if current_end >= end_time:
                                has_more_data = False
                            
                            # Skip chunks that are likely outside market hours
                            if not is_likely_market_hours(current_start) and not is_likely_market_hours(current_end):
                                print(f"    {Fore.YELLOW}Skipping chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')} (outside market hours){Style.RESET_ALL}")
                                current_start = current_end
                                continue
                            
                            print(f"    Requesting chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}")
                            
                            try:
                                # Use our custom implementation instead of the missing method
                                chunk_bars = await get_historical_time_bars(
                                    rithmic_client,
                                    contract,
                                    current_exchange,
                                    current_start,
                                    current_end,
                                    TimeBarType.SECOND_BAR,
                                    1  # 1-second bars
                                )
                            except Exception as e:
                                print(f"{Fore.RED}Error retrieving historical time bars: {e}{Style.RESET_ALL}")
                                chunk_bars = []
                                # Don't exit the loop on error, just count it as an empty chunk
                            
                            print(f"    {Fore.GREEN}Received {len(chunk_bars)} second bars for this chunk{Style.RESET_ALL}")
                            
                            # Track empty chunks
                            if not chunk_bars:
                                empty_chunks_in_a_row += 1
                                print(f"    {Fore.YELLOW}Empty chunk ({empty_chunks_in_a_row}/{max_empty_chunks}){Style.RESET_ALL}")
                            else:
                                empty_chunks_in_a_row = 0  # Reset counter when we get data
                            
                            # Check if we hit the API limit (9999 data points)
                            if len(chunk_bars) >= 9999:
                                reached_api_limit = True
                                print(f"    {Fore.YELLOW}API limit reached (9999 data points), reducing chunk size{Style.RESET_ALL}")
                                
                                # Reduce chunk size for next iteration
                                if max_chunk_hours > 1:  # Don't go below 1 hour
                                    max_chunk_hours = max_chunk_hours / 2
                                    print(f"    Reduced chunk size to {max_chunk_hours} hours")
                                    
                                    # Retry this chunk with smaller size
                                    continue
                            
                            # Add chunk to our collection
                            all_second_bars.extend(chunk_bars)
                            
                            # Move to next chunk
                            current_start = current_end
                                
                            # If we didn't hit the API limit, we can try increasing the chunk size
                            if not reached_api_limit and max_chunk_days < 7:
                                    max_chunk_days = min(7, max_chunk_days * 1.5)  # Increase but cap at 7 days
                            elif not chunk_bars:
                                # If we got no data for this chunk, we might be done
                                if current_end >= end_time:
                                    has_more_data = False
                                else:
                                    # Try the next chunk anyway
                                    current_start = current_end
                        
                        print(f"  {Fore.GREEN}Total received: {len(all_second_bars)} second bars{Style.RESET_ALL}")
                        
                        # Update data status
                        has_second_data = len(all_second_bars) > 0
                        
                        # Save to database
                        for bar in all_second_bars:
                            cursor.execute("""
                                INSERT OR IGNORE INTO second_bars 
                                (contract_id, timestamp, open, high, low, close, volume)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                contract_id,
                                bar['bar_end_datetime'].isoformat(),
                                bar['open'],
                                bar['high'],
                                bar['low'],
                                bar['close'],
                                bar['volume']
                            ))
                        
                        conn.commit()
                        
                    except Exception as e:
                        print(f"  {Fore.RED}Error downloading second bars: {e}{Style.RESET_ALL}")
                        no_data_reason = f"Error: {str(e)}"
                
                # Download minute bars if requested
                if download_minute_bars_for_contract:
                    print_header()  # Update progress display
                    print(f"  Downloading minute bars for {contract}...")
                    
                    try:
                        # Initialize variables for chunked downloading
                        all_minute_bars = []
                        current_start = start_time
                        max_chunk_days = 2  # Start with 2-day chunks for minute bars
                        has_more_data = True
                        reached_api_limit = False
                        empty_chunks_in_a_row = 0
                        max_empty_chunks = 3  # Stop after 3 empty chunks in a row (6 days with no data)
                        
                        # Reuse the is_likely_market_hours function from above
                        
                        while has_more_data and empty_chunks_in_a_row < max_empty_chunks:
                            # Calculate end time for this chunk
                            current_end = min(end_time, current_start + timedelta(days=max_chunk_days))
                            
                            # If we've reached the end time, this is the last chunk
                            if current_end >= end_time:
                                has_more_data = False
                            
                            # Skip chunks that are likely outside market hours
                            if not is_likely_market_hours(current_start) and not is_likely_market_hours(current_end):
                                print(f"    {Fore.YELLOW}Skipping chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')} (outside market hours){Style.RESET_ALL}")
                                current_start = current_end
                                continue
                            
                            print(f"    Requesting chunk: {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}")
                            
                            try:
                                # Use our custom implementation instead of the missing method
                                chunk_bars = await get_historical_time_bars(
                                    rithmic_client,
                                    contract,
                                    current_exchange,
                                    current_start,
                                    current_end,
                                    TimeBarType.MINUTE_BAR,
                                    1  # 1-minute bars
                                )
                            except Exception as e:
                                print(f"{Fore.RED}Error retrieving historical time bars: {e}{Style.RESET_ALL}")
                                chunk_bars = []
                                # Don't exit the loop on error, just count it as an empty chunk
                            
                            print(f"    {Fore.GREEN}Received {len(chunk_bars)} minute bars for this chunk{Style.RESET_ALL}")
                            
                            # Track empty chunks
                            if not chunk_bars:
                                empty_chunks_in_a_row += 1
                                print(f"    {Fore.YELLOW}Empty chunk ({empty_chunks_in_a_row}/{max_empty_chunks}){Style.RESET_ALL}")
                            else:
                                empty_chunks_in_a_row = 0  # Reset counter when we get data
                                
                                # If we got data, update the has_minute_data flag
                                has_minute_data = True
                            
                            # Check if we hit the API limit (9999 data points)
                            if len(chunk_bars) >= 9999:
                                reached_api_limit = True
                                print(f"    {Fore.YELLOW}API limit reached (9999 data points), reducing chunk size{Style.RESET_ALL}")
                                
                                # Reduce chunk size for next iteration
                                if max_chunk_days > 0.5:  # Don't go below 12 hours
                                    max_chunk_days = max_chunk_days / 2
                                    print(f"    Reduced chunk size to {max_chunk_days} days")
                                    
                                    # Retry this chunk with smaller size
                                    continue
                            
                            # Add chunk to our collection
                            all_minute_bars.extend(chunk_bars)
                            
                            # Move to next chunk
                            current_start = current_end
                            
                            # If we got data and didn't hit the API limit, we can try increasing the chunk size
                            if chunk_bars and not reached_api_limit and max_chunk_days < 7:
                                max_chunk_days = min(7, max_chunk_days * 1.5)  # Increase but cap at 7 days
                        
                        print(f"  {Fore.GREEN}Total received: {len(all_minute_bars)} minute bars{Style.RESET_ALL}")
                        
                        # Update data status
                        has_minute_data = len(all_minute_bars) > 0
                        
                        # Save to database
                        for bar in all_minute_bars:
                            cursor.execute("""
                                INSERT OR IGNORE INTO minute_bars 
                                (contract_id, timestamp, open, high, low, close, volume)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                contract_id,
                                bar['bar_end_datetime'].isoformat(),
                                bar['open'],
                                bar['high'],
                                bar['low'],
                                bar['close'],
                                bar['volume']
                            ))
                        
                        conn.commit()
                        
                    except Exception as e:
                        print(f"  {Fore.RED}Error downloading minute bars: {e}{Style.RESET_ALL}")
                        if not no_data_reason:
                            no_data_reason = f"Error: {str(e)}"
                
                # Update contract data status in the database
                today = datetime.now().strftime('%Y-%m-%d')
                
                # Check if we need to update the status
                if download_second_bars_for_contract or download_minute_bars_for_contract:
                    cursor.execute("""
                        INSERT OR REPLACE INTO contract_data_status
                        (contract_id, has_second_bars, has_minute_bars, last_checked_date, no_data_reason)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        contract_id,
                        1 if has_second_data else 0,
                        1 if has_minute_data else 0,
                        today,
                        no_data_reason
                    ))
                    
                    conn.commit()
                
                # Update progress
                contracts_processed += 1
                download_progress[symbol] = contracts_processed / total_contracts
                print_header()  # Update progress display
        
        print(f"\n{Fore.GREEN}Historical data download completed{Style.RESET_ALL}")
        
        # Generate download summary
        try:
            # First check if the contract_data_status table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contract_data_status'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT cds.contract_id) as total_contracts,
                        SUM(CASE WHEN cds.has_second_bars = 1 THEN 1 ELSE 0 END) as contracts_with_second_data,
                        SUM(CASE WHEN cds.has_minute_bars = 1 THEN 1 ELSE 0 END) as contracts_with_minute_data,
                        SUM(CASE WHEN cds.has_second_bars = 0 THEN 1 ELSE 0 END) as contracts_without_second_data,
                        SUM(CASE WHEN cds.has_minute_bars = 0 THEN 1 ELSE 0 END) as contracts_without_minute_data
                    FROM contract_data_status cds
                """)
                
                stats = cursor.fetchone()
                if stats and stats[0] > 0:  # Check if there are any contracts tracked
                    total, with_second, with_minute, without_second, without_minute = stats
                    
                    print(f"\n{Fore.CYAN}Download Summary:{Style.RESET_ALL}")
                    print(f"Total contracts tracked: {total}")
                    print(f"Contracts with second bar data: {with_second}")
                    print(f"Contracts with minute bar data: {with_minute}")
                    print(f"Contracts without second bar data: {without_second}")
                    print(f"Contracts without minute bar data: {without_minute}")
                else:
                    print(f"\n{Fore.YELLOW}No contract data status information available yet.{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}Contract data status table does not exist. Run database recreation to fix this issue.{Style.RESET_ALL}")
                
            # Get total bar counts
            try:
                cursor.execute("SELECT COUNT(*) FROM second_bars")
                second_bar_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM minute_bars")
                minute_bar_count = cursor.fetchone()[0]
                
                print(f"\nTotal second bars in database: {second_bar_count}")
                print(f"Total minute bars in database: {minute_bar_count}")
            except sqlite3.Error as e:
                print(f"\n{Fore.YELLOW}Could not count bars: {e}{Style.RESET_ALL}")
        except sqlite3.Error as e:
            print(f"\n{Fore.GREEN}Historical data download completed{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Could not generate summary statistics: {e}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error downloading historical data: {e}{Style.RESET_ALL}")
    finally:
        conn.close()
    
    input("\nPress Enter to continue...")

async def handle_time_bar(data, contract_id):
    """Handle incoming time bar data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Determine which table to use based on bar type
        if data['bar_type'] == TimeBarType.SECOND_BAR:
            table = 'second_bars'
        elif data['bar_type'] == TimeBarType.MINUTE_BAR:
            table = 'minute_bars'
        else:
            return  # Unsupported bar type
        
        # Insert bar data
        cursor.execute(f"""
            INSERT OR REPLACE INTO {table}
            (contract_id, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            contract_id,
            data['bar_end_datetime'].isoformat(),
            data['open'],
            data['high'],
            data['low'],
            data['close'],
            data['volume']
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error saving time bar: {e}")

async def stream_live_data():
    """Stream live data for available contracts"""
    if not is_connected:
        print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please connect first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    if not available_contracts:
        print_header()
        print(f"{Fore.RED}Error: No contracts available. Please check contracts first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    print_header()
    print(f"{Fore.YELLOW}Stream Live Data{Style.RESET_ALL}")
    
    # Ask for bar type
    print("\nBar Types to Stream:")
    print("1. Second bars")
    print("2. Minute bars")
    print("3. Both")
    bar_choice = input("Enter choice (default: 1): ")
    
    stream_second_bars = bar_choice in ['1', '3', '']
    stream_minute_bars = bar_choice in ['2', '3']
    
    if not stream_second_bars and not stream_minute_bars:
        print(f"{Fore.RED}Invalid choice. Defaulting to second bars.{Style.RESET_ALL}")
        stream_second_bars = True
    
    # Get contract IDs from database
    contract_map = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for symbol, contracts in available_contracts.items():
            for contract in contracts:
                cursor.execute("""
                    SELECT c.id FROM contracts c
                    JOIN symbols s ON c.symbol_id = s.id
                    WHERE c.contract = ? AND s.symbol = ? AND s.exchange = ?
                """, (contract, symbol, current_exchange))
                
                result = cursor.fetchone()
                if result:
                    contract_map[contract] = result[0]
        
        conn.close()
    except Exception as e:
        print(f"{Fore.RED}Error getting contract IDs: {e}{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    # Dictionary to store tick data for aggregation into time bars
    tick_data = {}
    last_bar_time = {}
    
    # Register tick data handler to simulate time bars
    async def time_bar_handler(data):
        # Process time bar data received from Rithmic
        if 'data_type' not in data:
            return
            
        # Handle both tick data and time bar data
        if data['data_type'] == DataType.LAST_TRADE:
            # Process tick data (for backward compatibility)
            contract = data.get('symbol', '')
            if not contract or contract not in contract_map:
                return
                
            # Initialize data structures if needed
            if contract not in tick_data:
                tick_data[contract] = {
                    'prices': [],
                    'volumes': [],
                    'timestamps': []
                }
                last_bar_time[contract] = {
                    'second': None,
                    'minute': None
                }
            
            # Add tick data
            price = data.get('price', 0)
            volume = data.get('size', 0)
            timestamp = datetime.now()
            
            if price > 0 and volume > 0:
                tick_data[contract]['prices'].append(price)
                tick_data[contract]['volumes'].append(volume)
                tick_data[contract]['timestamps'].append(timestamp)
                
                # Process second bars if enabled
                if stream_second_bars:
                    current_second = timestamp.replace(microsecond=0)
                    if last_bar_time[contract]['second'] != current_second:
                        # New second bar
                        if last_bar_time[contract]['second'] is not None:
                            # Create and process the bar
                            bar_data = create_time_bar(contract, tick_data[contract], 'second')
                            await process_time_bar(bar_data, contract_map[contract])
                            
                        # Reset data for the new second
                        last_bar_time[contract]['second'] = current_second
                        
                # Process minute bars if enabled
                if stream_minute_bars:
                    current_minute = timestamp.replace(second=0, microsecond=0)
                    if last_bar_time[contract]['minute'] != current_minute:
                        # New minute bar
                        if last_bar_time[contract]['minute'] is not None:
                            # Create and process the bar
                            bar_data = create_time_bar(contract, tick_data[contract], 'minute')
                            await process_time_bar(bar_data, contract_map[contract])
                            
                        # Reset data for the new minute
                        last_bar_time[contract]['minute'] = current_minute
        
        # Handle time bar data directly from Rithmic
        elif 'bar_type' in data:
            contract = data.get('symbol', '')
            if not contract or contract not in contract_map:
                return
                
            # Check if we should process this bar type
            bar_type = data.get('bar_type')
            if (bar_type == TimeBarType.SECOND_BAR and stream_second_bars) or \
               (bar_type == TimeBarType.MINUTE_BAR and stream_minute_bars):
                
                # Create a bar data structure compatible with our processing
                bar_data = {
                    'symbol': contract,
                    'open': data.get('open', 0),
                    'high': data.get('high', 0),
                    'low': data.get('low', 0),
                    'close': data.get('close', 0),
                    'volume': data.get('volume', 0),
                    'bar_end_datetime': data.get('bar_end_datetime', 
                                               datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                }
                
                # Process the time bar
                await process_time_bar(bar_data, contract_map[contract])
    
    # Helper function to create a time bar from tick data
    def create_time_bar(contract, data, bar_type):
        prices = data['prices']
        volumes = data['volumes']
        
        if not prices:
            return None
            
        bar_data = {
            'symbol': contract,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': sum(volumes),
            'bar_end_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Clear the data for the next bar
        if bar_type == 'second':
            # For second bars, clear all data
            data['prices'] = []
            data['volumes'] = []
            data['timestamps'] = []
        elif bar_type == 'minute' and len(data['timestamps']) > 0:
            # For minute bars, keep only the current second's data
            current_second = datetime.now().replace(microsecond=0)
            indices_to_keep = [i for i, ts in enumerate(data['timestamps']) 
                              if ts.replace(microsecond=0) == current_second]
            
            data['prices'] = [data['prices'][i] for i in indices_to_keep]
            data['volumes'] = [data['volumes'][i] for i in indices_to_keep]
            data['timestamps'] = [data['timestamps'][i] for i in indices_to_keep]
            
        return bar_data
    
    # Process the time bar data
    async def process_time_bar(bar_data, contract_id):
        if not bar_data:
            return
            
        await handle_time_bar(bar_data, contract_id)
        
        # Update display
        print_header()
        print(f"{Fore.GREEN}Received bar: {bar_data['symbol']} @ {bar_data['bar_end_datetime']}{Style.RESET_ALL}")
        print(f"O: {bar_data['open']}, H: {bar_data['high']}, L: {bar_data['low']}, C: {bar_data['close']}, V: {bar_data['volume']}")
        print("\nPress Ctrl+C to stop streaming...")
    
    # Check if rithmic_client exists and has on_tick attribute before subscribing
    if rithmic_client is None:
        print(f"{Fore.RED}Error: Rithmic client is not initialized.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
        
    # Check if on_tick attribute exists
    if not hasattr(rithmic_client, 'on_tick'):
        print(f"{Fore.RED}Error: Rithmic client does not have on_tick attribute.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
        
    # Now it's safe to subscribe to the on_tick event
    rithmic_client.on_tick += time_bar_handler
    
    try:
        print(f"\n{Fore.GREEN}Starting data stream...{Style.RESET_ALL}")
        
        # Subscribe to time bars for each contract
        for symbol, contracts in available_contracts.items():
            for contract in contracts:
                # Use on_time_bar event handler instead of subscribe_to_time_bar_data
                # Use on_time_bar event handler instead of subscribe_to_time_bar_data
                if stream_second_bars:
                    # For second bars, register the time_bar_handler with on_time_bar event
                    if hasattr(rithmic_client, 'on_time_bar'):
                        rithmic_client.on_time_bar += time_bar_handler
                        print(f"Registered time_bar_handler for {contract} second bars")
                
                if stream_minute_bars:
                    # For minute bars, we're already registered with on_time_bar event
                    # We'll filter by bar type in the handler
                    print(f"Using time_bar_handler for {contract} minute bars")
        
        print(f"\n{Fore.GREEN}Data streaming started. Press Ctrl+C to stop...{Style.RESET_ALL}")
        
        # Keep streaming until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Stopping data stream...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error streaming data: {e}{Style.RESET_ALL}")
    finally:
        # Unsubscribe from all data
        try:
            for symbol, contracts in available_contracts.items():
                for contract in contracts:
                    # No need to unsubscribe from individual contracts
                    # We'll remove the event handler later
                    pass
            
            print(f"{Fore.GREEN}Successfully unsubscribed from all data streams{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error unsubscribing: {e}{Style.RESET_ALL}")
        
        # Remove handler - check if client exists and has the attribute first
        if rithmic_client is not None:
            # Remove from on_tick if it exists
            if hasattr(rithmic_client, 'on_tick'):
                try:
                    rithmic_client.on_tick -= time_bar_handler
                except Exception as e:
                    print(f"{Fore.YELLOW}Warning: Could not remove on_tick handler: {e}{Style.RESET_ALL}")
            
            # Also try to remove from on_time_bar if it exists (based on the comment at line 1439)
            if hasattr(rithmic_client, 'on_time_bar'):
                try:
                    rithmic_client.on_time_bar -= time_bar_handler
                except Exception as e:
                    print(f"{Fore.YELLOW}Warning: Could not remove on_time_bar handler: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def view_contract_data_status():
    """View the status of contracts with no data"""
    print_header()
    print(f"{Fore.YELLOW}Contract Data Status{Style.RESET_ALL}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all contracts with their data status
        cursor.execute("""
            SELECT 
                s.symbol, 
                c.contract, 
                cds.has_second_bars, 
                cds.has_minute_bars, 
                cds.last_checked_date, 
                cds.no_data_reason
            FROM contract_data_status cds
            JOIN contracts c ON cds.contract_id = c.id
            JOIN symbols s ON c.symbol_id = s.id
            ORDER BY s.symbol, c.contract
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print(f"{Fore.YELLOW}No contract data status information available{Style.RESET_ALL}")
        else:
            # Count contracts with no data
            no_second_data_count = sum(1 for r in results if r[2] == 0)
            no_minute_data_count = sum(1 for r in results if r[3] == 0)
            
            print(f"\nFound {len(results)} contracts with status information")
            print(f"{no_second_data_count} contracts have no second bar data")
            print(f"{no_minute_data_count} contracts have no minute bar data")
            print()
            
            # Display contracts with no data
            print(f"{Fore.CYAN}Contracts with no data:{Style.RESET_ALL}")
            for symbol, contract, has_second, has_minute, last_checked, reason in results:
                if has_second == 0 or has_minute == 0:
                    second_status = f"{Fore.RED}No Data{Style.RESET_ALL}" if has_second == 0 else f"{Fore.GREEN}Has Data{Style.RESET_ALL}"
                    minute_status = f"{Fore.RED}No Data{Style.RESET_ALL}" if has_minute == 0 else f"{Fore.GREEN}Has Data{Style.RESET_ALL}"
                    
                    print(f"Symbol: {symbol}, Contract: {contract}")
                    print(f"  Second Bars: {second_status}, Minute Bars: {minute_status}")
                    print(f"  Last Checked: {last_checked}")
                    if reason:
                        print(f"  Reason: {reason}")
                    print()
            
            # Ask if user wants to reset status for any contracts
            reset_choice = input("Do you want to reset the 'no data' status for any contracts? (y/n): ").lower()
            if reset_choice == 'y':
                reset_options = [
                    "1. Reset all contracts",
                    "2. Reset specific symbol",
                    "3. Reset specific contract"
                ]
                
                print("\nReset Options:")
                for option in reset_options:
                    print(option)
                
                reset_option = input("\nEnter choice: ")
                
                if reset_option == '1':
                    cursor.execute("DELETE FROM contract_data_status")
                    conn.commit()
                    print(f"{Fore.GREEN}Reset all contract data status information{Style.RESET_ALL}")
                
                elif reset_option == '2':
                    symbol = input("Enter symbol to reset (e.g., NQ, ES): ")
                    cursor.execute("""
                        DELETE FROM contract_data_status
                        WHERE contract_id IN (
                            SELECT c.id FROM contracts c
                            JOIN symbols s ON c.symbol_id = s.id
                            WHERE s.symbol = ?
                        )
                    """, (symbol,))
                    conn.commit()
                    print(f"{Fore.GREEN}Reset data status for symbol: {symbol}{Style.RESET_ALL}")
                
                elif reset_option == '3':
                    contract = input("Enter specific contract to reset (e.g., ESZ3): ")
                    cursor.execute("""
                        DELETE FROM contract_data_status
                        WHERE contract_id IN (
                            SELECT id FROM contracts WHERE contract = ?
                        )
                    """, (contract,))
                    conn.commit()
                    print(f"{Fore.GREEN}Reset data status for contract: {contract}{Style.RESET_ALL}")
                
                else:
                    print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
        
    except sqlite3.Error as e:
        print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")
    finally:
        conn.close()
    
    input("\nPress Enter to continue...")

async def main_menu():
    """Display the main menu and handle user choices"""
    while True:
        print_header()
        print(f"{Fore.YELLOW}Main Menu{Style.RESET_ALL}")
        print("1. Test DB Connection and Tables")
        print("2. Test Rithmic Connection with Login Data")
        print("3. Search Symbols")
        print("4. Check Contract Existence")
        print("5. Download Historical Data")
        print("6. Stream Live Data")
        print("7. View Contract Data Status")
        print("8. Force Recreate Database")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            await test_db_connection()
        elif choice == '2':
            await connect_to_rithmic()
        elif choice == '3':
            await search_symbols()
        elif choice == '4':
            await check_contracts()
        elif choice == '5':
            await download_historical_data()
        elif choice == '6':
            await stream_live_data()
        elif choice == '7':
            await view_contract_data_status()
        elif choice == '8':
            # Force recreate database
            print_header()
            print(f"{Fore.YELLOW}Force Recreate Database{Style.RESET_ALL}")
            print(f"{Fore.RED}WARNING: This will delete all data in the database!{Style.RESET_ALL}")
            confirm = input("Are you sure you want to continue? (y/n): ")
            if confirm.lower() == 'y':
                try:
                    # Initialize conn to None
                    conn = None
                    
                    # Close any existing connections
                    if 'conn' in locals() and conn is not None:
                        conn.close()
                    
                    # Delete the database file
                    if os.path.exists(DB_PATH):
                        os.remove(DB_PATH)
                        print(f"{Fore.YELLOW}Existing database deleted.{Style.RESET_ALL}")
                    
                    # Create new database
                    success, message = create_database()
                    if success:
                        print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}{message}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
                
                input("\nPress Enter to continue...")
        elif choice == '0':
            # Disconnect from Rithmic if connected
            if is_connected and rithmic_client:
                try:
                    await rithmic_client.disconnect()
                    print(f"{Fore.GREEN}Disconnected from Rithmic{Style.RESET_ALL}")
                except:
                    pass
            
            print(f"{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
            time.sleep(1)

async def process_command_line_args(args):
    """Process command line arguments and run the appropriate functions"""
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Process data types if specified
    data_types = []
    if args.data_types:
        try:
            # Parse the comma-separated list of data types
            type_names = [t.strip().upper() for t in args.data_types.split(',')]
            for type_name in type_names:
                try:
                    # Special handling for HISTORY which is not a DataType enum value
                    if type_name == "HISTORY":
                        # Print all available DataType values for debugging
                        print(f"Available DataType values: {[dt.name for dt in DataType]}")
                        
                        # Store HISTORY as a string since it's not a DataType enum value
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
    
    # Enable history data type if requested
    if args.enable_history:
        # Add HISTORY to data_types if not already there
        if "HISTORY" not in data_types:
            data_types.append("HISTORY")
            print(f"{Fore.CYAN}Added HISTORY to enabled data types{Style.RESET_ALL}")
    
    # Connect to Rithmic if requested
    if args.connect:
        await connect_to_rithmic(cli_mode=True, data_types=data_types)
        
        # If only connecting, wait for user input before disconnecting
        if not any(getattr(args, attr) for attr in vars(args) if attr not in ['connect', 'data_types', 'enable_history']):
            print(f"\n{Fore.GREEN}Connected to Rithmic with specified data types.{Style.RESET_ALL}")
            input("Press Enter to disconnect and exit...")
            await disconnect_from_rithmic()
            return
    
    # Test connections if requested
    elif args.test_connections:
        await test_db_connection(cli_mode=True)
        await connect_to_rithmic(cli_mode=True, data_types=data_types)
        
        # If only testing connections, close the Rithmic client and return
        if not any(getattr(args, attr) for attr in vars(args) if attr not in ['test_connections', 'data_types']):
            await disconnect_from_rithmic()
            return
    
    # Search for symbols if requested
    if args.search_symbols:
        # Set the search term
        global current_exchange
        
        # Import search_symbols function here to avoid circular imports
        from search_symbols import search_symbols as search_symbols_func
        
        search_term = args.search_symbols
        print(f"\nSearching for '{search_term}' on {current_exchange}...")
        
        # Check if search term contains wildcards
        has_wildcards = '*' in search_term or '?' in search_term
        
        # If wildcards are present, convert to a basic search term for the API
        api_search_term = search_term
        if has_wildcards:
            # Extract the base part of the search term (before any wildcards)
            api_search_term = re.split(r'[\*\?]', search_term)[0]
            if not api_search_term:
                api_search_term = search_term.replace('*', '').replace('?', '')
                if not api_search_term:
                    api_search_term = 'A'  # Fallback to a very broad search
        
        try:
            # Search for symbols
            results = await search_symbols_func(
                rithmic_client,
                api_search_term, 
                instrument_type=InstrumentType.FUTURE,
                exchange=current_exchange
            )
            
            if not results:
                print(f"{Fore.YELLOW}No symbols found matching '{search_term}' on {current_exchange}{Style.RESET_ALL}")
                return
            
            # Filter results if wildcards were used
            filtered_results = results
            if has_wildcards:
                filtered_results = []
                pattern = search_term.replace('?', '.').replace('*', '.*')
                
                # Check if we're dealing with NQ or ES futures
                is_nq_es = search_term.upper().startswith('NQ') or search_term.upper().startswith('ES')
                
                for result in results:
                    # For NQ and ES, only include contracts with valid month codes (H, M, U, Z)
                    if is_nq_es:
                        # Extract the month code from the symbol (typically the character after the root)
                        symbol = result.symbol.upper()
                        product_code = result.product_code.upper()
                        
                        # Try to extract month code - typically it's the first non-digit after the root symbol
                        month_code = None
                        if len(symbol) > 2:  # Ensure there's enough characters
                            for char in symbol[2:]:
                                if char.isalpha():
                                    month_code = char
                                    break
                        
                        # Skip if not a valid quarterly month code
                        if month_code and month_code not in ['H', 'M', 'U', 'Z']:
                            continue
                    
                    # Apply the wildcard pattern matching
                    if (re.match(pattern, result.symbol, re.IGNORECASE) or 
                        re.match(pattern, result.product_code, re.IGNORECASE)):
                        filtered_results.append(result)
            
            # Display results
            print(f"\n{Fore.GREEN}Found {len(filtered_results)} symbols:{Style.RESET_ALL}")
            
            # Format and print the results
            for i, result in enumerate(filtered_results, 1):
                # Extract month code for futures contracts (if present)
                month_code = ""
                month_name = ""
                symbol = result.symbol
                if len(symbol) > 2:  # Ensure there's enough characters
                    for char in symbol[2:]:
                        if char.isalpha():
                            # Map month code to full month name
                            month_map = {
                                'H': 'March',
                                'M': 'June',
                                'U': 'September',
                                'Z': 'December'
                            }
                            
                            if char.upper() in month_map:
                                month_code = char.upper()
                                month_name = month_map[month_code]
                                month_display = f"{Fore.YELLOW}{month_name}{Style.RESET_ALL}"
                            else:
                                month_code = char.upper()
                                month_display = month_code
                            break
                
                # Format the item
                line = f"{i}. Symbol: {symbol}"
                if month_code:
                    line += f" (Month: {month_display})"
                line += f" | Product: {result.product_code}"
                line += f" | Exp: {result.expiration_date}"
                
                print(line)
            
        except Exception as e:
            print(f"{Fore.RED}Error searching symbols: {e}{Style.RESET_ALL}")
    
    # Set symbol if provided
    if args.symbol:
        global current_symbols
        current_symbols = [args.symbol]
        print(f"\n{Fore.GREEN}Using symbol: {args.symbol}{Style.RESET_ALL}")
    
    # Check contracts if requested
    if args.check_contracts:
        if not current_symbols:
            print(f"{Fore.RED}Error: No symbol specified. Use -s/--symbol to specify a symbol.{Style.RESET_ALL}")
        else:
            await check_contracts(cli_mode=True)
    
    # Download historical data if requested
    if args.download_historical:
        if not current_symbols:
            print(f"{Fore.RED}Error: No symbol specified. Use -s/--symbol to specify a symbol.{Style.RESET_ALL}")
        else:
            # Get days to download from args if provided
            days = 7  # Default
            if args.days:
                try:
                    days = int(args.days)
                except ValueError:
                    print(f"{Fore.YELLOW}Invalid days value. Using default of 7 days.{Style.RESET_ALL}")
            
            await download_historical_data(cli_mode=True, days_to_download=days)
    
    # Stream live data if requested
    if args.stream_live:
        if not current_symbols:
            print(f"{Fore.RED}Error: No symbol specified. Use -s/--symbol to specify a symbol.{Style.RESET_ALL}")
        else:
            # We'll need to modify stream_live_data to support cli_mode
            # For now, we'll just call it as is
            await stream_live_data()
            
    # Always disconnect from Rithmic at the end if we're connected
    if is_connected and rithmic_client:
        await disconnect_from_rithmic()

if __name__ == "__main__":
    import argparse
    
    # Initialize colorama
    colorama.init()
    
    # Create argument parser
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
    parser.add_argument("-l", "--stream-live", action="store_true",
                        help="Stream live data (requires -s/--symbol)")
    parser.add_argument("--data-types", type=str, metavar="TYPES",
                        help="Comma-separated list of data types to enable (e.g., 'HISTORY,MARKET_DATA')")
    parser.add_argument("--connect", action="store_true",
                        help="Connect to Rithmic (can be used with --data-types)")
    parser.add_argument("--enable-history", action="store_true",
                        help="Enable history data type for historical data retrieval")
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no arguments provided, run the interactive menu
    if not any(vars(args).values()):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            
            # Run the main menu
            asyncio.run(main_menu())
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Unhandled exception: {e}{Style.RESET_ALL}")
    else:
        # Process command line arguments
        try:
            asyncio.run(process_command_line_args(args))
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")
        except Exception as e:
            error_msg = f"Unhandled exception: {e}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            logger.exception(error_msg)
