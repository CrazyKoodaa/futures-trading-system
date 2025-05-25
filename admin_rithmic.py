#!/usr/bin/env python
# admin_rithmic.py
"""
Admin script for Rithmic data collection with interactive menu
"""
import os
import sys
import time
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import colorama
from colorama import Fore, Back, Style

# Import Rithmic components
from config.chicago_gateway_config import get_chicago_gateway_config
from async_rithmic import RithmicClient, TimeBarType, DataType, InstrumentType
from async_rithmic import ReconnectionSettings, RetrySettings

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

# Global variables
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
        print(f"{Fore.GREEN}Connection Status: Connected{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Connection Status: Disconnected{Style.RESET_ALL}")
    
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
            bar = "#" * int(progress * 30) + "." * (30 - int(progress * 30))
            print(f"{symbol}: [{bar}] {progress*100:.1f}%")
    
    print(f"{Fore.CYAN}{'-' * 80}{Style.RESET_ALL}\n")

def create_database():
    """Create SQLite database and tables if they don't exist"""
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
        
        conn.commit()
        conn.close()
        return True, "Database created successfully"
    except Exception as e:
        return False, f"Error creating database: {e}"

async def test_db_connection():
    """Test database connection and tables"""
    print_header()
    print(f"{Fore.YELLOW}Testing database connection...{Style.RESET_ALL}")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        success, message = create_database()
        if not success:
            print(f"{Fore.RED}{message}{Style.RESET_ALL}")
            choice = input("\nWould you like to recreate the database? (y/n): ")
            if choice.lower() == 'y':
                try:
                    os.remove(DB_PATH)
                    success, message = create_database()
                    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
            return
    
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
        
        conn.close()
        
        print(f"\n{Fore.GREEN}Database check completed successfully{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")
        choice = input("\nWould you like to recreate the database? (y/n): ")
        if choice.lower() == 'y':
            try:
                os.remove(DB_PATH)
                success, message = create_database()
                print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error recreating database: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def connect_to_rithmic():
    """Connect to Rithmic with login data"""
    global rithmic_client, is_connected
    
    print_header()
    print(f"{Fore.YELLOW}Connecting to Rithmic...{Style.RESET_ALL}")
    
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
        rithmic_client = RithmicClient(
            user=config['rithmic']['user'],
            password=config['rithmic']['password'],
            system_name=config['rithmic']['system_name'],
            app_name=config['rithmic']['app_name'],
            app_version=config['rithmic']['app_version'],
            gateway=config['rithmic']['gateway'],
            reconnection_settings=reconnection,
            retry_settings=retry
        )
        
        # Connect to Rithmic
        print("\nAttempting connection...")
        await rithmic_client.connect()
        is_connected = True
        
        print(f"\n{Fore.GREEN}Successfully connected to Rithmic!{Style.RESET_ALL}")
        
    except Exception as e:
        is_connected = False
        print(f"\n{Fore.RED}Connection error: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def search_symbols():
    """Search for symbols in Rithmic"""
    global current_symbols, current_exchange
    
    if not is_connected:
        print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please connect first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    print_header()
    print(f"{Fore.YELLOW}Symbol Search{Style.RESET_ALL}")
    
    # Get search term from user
    search_term = input("Enter search term (e.g., ES, NQ): ")
    if not search_term:
        print(f"{Fore.RED}Search term cannot be empty{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    # Get exchange from user
    exchange = input(f"Enter exchange (default: {current_exchange}): ")
    if exchange:
        current_exchange = exchange
    
    try:
        print(f"\nSearching for '{search_term}' on {current_exchange}...")
        
        # Search for symbols
        results = await rithmic_client.search_symbols(
            search_term, 
            instrument_type=InstrumentType.FUTURE,
            exchange=current_exchange
        )
        
        if not results:
            print(f"{Fore.YELLOW}No symbols found matching '{search_term}' on {current_exchange}{Style.RESET_ALL}")
            input("\nPress Enter to continue...")
            return
        
        # Display results
        print(f"\n{Fore.GREEN}Found {len(results)} symbols:{Style.RESET_ALL}")
        symbols = []
        
        for i, result in enumerate(results, 1):
            symbols.append(result.product_code)
            print(f"{i}. Symbol: {result.symbol}")
            print(f"   Product Code: {result.product_code}")
            print(f"   Name: {result.symbol_name}")
            print(f"   Type: {result.instrument_type}")
            print(f"   Expiration: {result.expiration_date}")
            print()
        
        # Ask user which symbols to use
        choice = input("Enter symbol numbers to use (comma-separated, or 'all'): ")
        
        if choice.lower() == 'all':
            current_symbols = list(set(symbols))
        else:
            try:
                indices = [int(idx.strip()) - 1 for idx in choice.split(',') if idx.strip()]
                current_symbols = [symbols[idx] for idx in indices if 0 <= idx < len(symbols)]
            except (ValueError, IndexError):
                print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
                input("\nPress Enter to continue...")
                return
        
        print(f"\n{Fore.GREEN}Selected symbols: {', '.join(current_symbols)}{Style.RESET_ALL}")
        
        # Save symbols to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for symbol in current_symbols:
            cursor.execute(
                "INSERT OR IGNORE INTO symbols (symbol, exchange, description) VALUES (?, ?, ?)",
                (symbol, current_exchange, f"Added via search on {datetime.now().isoformat()}")
            )
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}Error searching symbols: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def check_contracts():
    """Check which contracts can be accessed for the searched symbols"""
    global available_contracts
    
    if not is_connected:
        print_header()
        print(f"{Fore.RED}Error: Not connected to Rithmic. Please connect first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    if not current_symbols:
        print_header()
        print(f"{Fore.RED}Error: No symbols selected. Please search for symbols first.{Style.RESET_ALL}")
        input("\nPress Enter to continue...")
        return
    
    print_header()
    print(f"{Fore.YELLOW}Checking Available Contracts{Style.RESET_ALL}")
    print(f"Symbols: {', '.join(current_symbols)}")
    print(f"Exchange: {current_exchange}")
    print()
    
    available_contracts = {}
    
    try:
        # Get current date for reference
        now = datetime.now()
        
        for symbol in current_symbols:
            print(f"Checking contracts for {symbol}...")
            
            # Get front month contract
            front_month = await rithmic_client.get_front_month_contract(symbol, current_exchange)
            
            # Search for all contracts for this symbol
            results = await rithmic_client.search_symbols(
                symbol, 
                instrument_type=InstrumentType.FUTURE,
                exchange=current_exchange
            )
            
            # Filter and sort contracts
            contracts = []
            for result in results:
                if result.product_code == symbol:
                    contracts.append(result.symbol)
            
            contracts.sort()
            available_contracts[symbol] = contracts
            
            print(f"  Front month: {front_month}")
            print(f"  All contracts: {', '.join(contracts)}")
            print()
            
            # Save contracts to database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get symbol_id
            cursor.execute("SELECT id FROM symbols WHERE symbol = ? AND exchange = ?", (symbol, current_exchange))
            result = cursor.fetchone()
            
            if result:
                symbol_id = result[0]
                
                for contract in contracts:
                    # Extract expiration date from contract (if possible)
                    expiration = None
                    if len(contract) > len(symbol):
                        # Simple extraction, would need refinement for production
                        expiration = contract[len(symbol):]
                    
                    cursor.execute(
                        "INSERT OR IGNORE INTO contracts (symbol_id, contract, expiration_date) VALUES (?, ?, ?)",
                        (symbol_id, contract, expiration)
                    )
            
            conn.commit()
            conn.close()
        
        print(f"{Fore.GREEN}Contract check completed{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error checking contracts: {e}{Style.RESET_ALL}")
    
    input("\nPress Enter to continue...")

async def download_historical_data():
    """Download historical data for available contracts"""
    global download_progress
    
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
    print(f"{Fore.YELLOW}Download Historical Data{Style.RESET_ALL}")
    
    # Ask for date range
    days_input = input("Enter number of days to download (default: 7): ")
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
    
    # Set time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    print(f"\nDownloading data from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"Bar types: {'Second bars' if download_second_bars else ''}{' and ' if download_second_bars and download_minute_bars else ''}{'Minute bars' if download_minute_bars else ''}")
    
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
                print(f"  Downloading {contract}...")
                
                # Get contract_id from database
                cursor.execute("""
                    SELECT c.id FROM contracts c
                    JOIN symbols s ON c.symbol_id = s.id
                    WHERE c.contract = ? AND s.symbol = ? AND s.exchange = ?
                """, (contract, symbol, current_exchange))
                
                result = cursor.fetchone()
                if not result:
                    print(f"  {Fore.YELLOW}Contract {contract} not found in database, skipping{Style.RESET_ALL}")
                    continue
                
                contract_id = result[0]
                
                # Download second bars if requested
                if download_second_bars:
                    print_header()  # Update progress display
                    print(f"  Downloading second bars for {contract}...")
                    
                    try:
                        second_bars = await rithmic_client.get_historical_time_bars(
                            contract,
                            current_exchange,
                            start_time,
                            end_time,
                            TimeBarType.SECOND_BAR,
                            1  # 1-second bars
                        )
                        
                        print(f"  {Fore.GREEN}Received {len(second_bars)} second bars{Style.RESET_ALL}")
                        
                        # Save to database
                        for bar in second_bars:
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
                
                # Download minute bars if requested
                if download_minute_bars:
                    print_header()  # Update progress display
                    print(f"  Downloading minute bars for {contract}...")
                    
                    try:
                        minute_bars = await rithmic_client.get_historical_time_bars(
                            contract,
                            current_exchange,
                            start_time,
                            end_time,
                            TimeBarType.MINUTE_BAR,
                            1  # 1-minute bars
                        )
                        
                        print(f"  {Fore.GREEN}Received {len(minute_bars)} minute bars{Style.RESET_ALL}")
                        
                        # Save to database
                        for bar in minute_bars:
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
                
                # Update progress
                contracts_processed += 1
                download_progress[symbol] = contracts_processed / total_contracts
                print_header()  # Update progress display
        
        print(f"\n{Fore.GREEN}Historical data download completed{Style.RESET_ALL}")
        
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
    
    # Register time bar handler
    async def time_bar_handler(data):
        contract = data['symbol']
        if contract in contract_map:
            await handle_time_bar(data, contract_map[contract])
            
            # Update display
            print_header()
            print(f"{Fore.GREEN}Received bar: {contract} @ {data['bar_end_datetime']}{Style.RESET_ALL}")
            print(f"O: {data['open']}, H: {data['high']}, L: {data['low']}, C: {data['close']}, V: {data['volume']}")
            print("\nPress Ctrl+C to stop streaming...")
    
    rithmic_client.on_time_bar += time_bar_handler
    
    try:
        print(f"\n{Fore.GREEN}Starting data stream...{Style.RESET_ALL}")
        
        # Subscribe to time bars for each contract
        for symbol, contracts in available_contracts.items():
            for contract in contracts:
                if stream_second_bars:
                    await rithmic_client.subscribe_to_time_bar_data(
                        contract, current_exchange, TimeBarType.SECOND_BAR, 1
                    )
                    print(f"Subscribed to second bars for {contract}")
                
                if stream_minute_bars:
                    await rithmic_client.subscribe_to_time_bar_data(
                        contract, current_exchange, TimeBarType.MINUTE_BAR, 1
                    )
                    print(f"Subscribed to minute bars for {contract}")
        
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
                    if stream_second_bars:
                        await rithmic_client.unsubscribe_from_time_bar_data(
                            contract, current_exchange, TimeBarType.SECOND_BAR, 1
                        )
                    
                    if stream_minute_bars:
                        await rithmic_client.unsubscribe_from_time_bar_data(
                            contract, current_exchange, TimeBarType.MINUTE_BAR, 1
                        )
            
            print(f"{Fore.GREEN}Successfully unsubscribed from all data streams{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error unsubscribing: {e}{Style.RESET_ALL}")
        
        # Remove handler
        rithmic_client.on_time_bar -= time_bar_handler
    
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

if __name__ == "__main__":
    try:
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Run the main menu
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program terminated by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Unhandled exception: {e}{Style.RESET_ALL}")
        logger.exception("Unhandled exception in main")