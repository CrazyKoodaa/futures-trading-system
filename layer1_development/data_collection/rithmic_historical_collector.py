# rithmic_historical_collector.py
"""
Script to collect historical data from Rithmic
"""
import asyncio
import logging
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from config.chicago_gateway_config import get_chicago_gateway_config
from async_rithmic import RithmicClient, TimeBarType

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create data directories if they don't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
HISTORICAL_DIR = os.path.join(DATA_DIR, 'historical')
os.makedirs(HISTORICAL_DIR, exist_ok=True)

async def save_historical_data(data, symbol, data_type, start_date, end_date):
    """
    Save historical data to file
    
    Args:
        data: List of data points
        symbol: Symbol name
        data_type: Type of data (e.g., 'ticks', 'minute_bars')
        start_date: Start date of data
        end_date: End date of data
    """
    if not data:
        logger.warning(f"No data to save for {symbol} {data_type}")
        return
    
    # Format dates for filename
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    # Create directory for symbol if it doesn't exist
    symbol_dir = os.path.join(HISTORICAL_DIR, symbol)
    os.makedirs(symbol_dir, exist_ok=True)
    
    # Create filename
    filename = f"{symbol}_{data_type}_{start_str}_to_{end_str}.csv"
    filepath = os.path.join(symbol_dir, filename)
    
    try:
        # Convert to DataFrame for easier saving
        df = pd.DataFrame(data)
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(data)} {data_type} for {symbol} to {filepath}")
        
        # Also save metadata
        metadata = {
            'symbol': symbol,
            'data_type': data_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'count': len(data),
            'created_at': datetime.now().isoformat()
        }
        
        metadata_file = f"{os.path.splitext(filepath)[0]}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
    except Exception as e:
        logger.error(f"Error saving data for {symbol} {data_type}: {e}")

async def fetch_historical_data(client, symbols=['ES', 'NQ'], days=30):
    """
    Fetch historical data for specified symbols
    
    Args:
        client: RithmicClient instance
        symbols: List of symbol roots (e.g., ['ES', 'NQ'])
        days: Number of days of historical data to fetch
    """
    try:
        # Get front month contracts for each symbol
        contracts = []
        for symbol in symbols:
            try:
                contract = await client.get_front_month_contract(symbol, "CME")
                contracts.append((contract, "CME", symbol))
                logger.info(f"Front month contract for {symbol}: {contract}")
            except Exception as e:
                logger.error(f"Error getting front month contract for {symbol}: {e}")
        
        if not contracts:
            logger.error("No valid contracts found")
            return
        
        # Set time range for historical data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        logger.info(f"Fetching historical data from {start_time} to {end_time}")
        
        # Fetch historical data for each contract
        for contract, exchange, symbol_root in contracts:
            try:
                # Fetch daily bars
                logger.info(f"Fetching daily bars for {contract}")
                daily_bars = await client.get_historical_time_bars(
                    contract,
                    exchange,
                    start_time,
                    end_time,
                    TimeBarType.DAILY_BAR,
                    1
                )
                await save_historical_data(
                    daily_bars, 
                    symbol_root, 
                    'daily_bars', 
                    start_time, 
                    end_time
                )
                
                # Fetch hourly bars
                logger.info(f"Fetching hourly bars for {contract}")
                hourly_bars = await client.get_historical_time_bars(
                    contract,
                    exchange,
                    start_time,
                    end_time,
                    TimeBarType.MINUTE_BAR,
                    60
                )
                await save_historical_data(
                    hourly_bars, 
                    symbol_root, 
                    'hourly_bars', 
                    start_time, 
                    end_time
                )
                
                # Fetch 15-minute bars
                logger.info(f"Fetching 15-minute bars for {contract}")
                minute_bars_15 = await client.get_historical_time_bars(
                    contract,
                    exchange,
                    start_time,
                    end_time,
                    TimeBarType.MINUTE_BAR,
                    15
                )
                await save_historical_data(
                    minute_bars_15, 
                    symbol_root, 
                    'minute_bars_15', 
                    start_time, 
                    end_time
                )
                
                # Fetch 5-minute bars
                logger.info(f"Fetching 5-minute bars for {contract}")
                minute_bars_5 = await client.get_historical_time_bars(
                    contract,
                    exchange,
                    start_time,
                    end_time,
                    TimeBarType.MINUTE_BAR,
                    5
                )
                await save_historical_data(
                    minute_bars_5, 
                    symbol_root, 
                    'minute_bars_5', 
                    start_time, 
                    end_time
                )
                
                # Fetch 1-minute bars
                logger.info(f"Fetching 1-minute bars for {contract}")
                minute_bars_1 = await client.get_historical_time_bars(
                    contract,
                    exchange,
                    start_time,
                    end_time,
                    TimeBarType.MINUTE_BAR,
                    1
                )
                await save_historical_data(
                    minute_bars_1, 
                    symbol_root, 
                    'minute_bars_1', 
                    start_time, 
                    end_time
                )
                
                # Fetch tick data for the last day only (to avoid too much data)
                tick_end = end_time
                tick_start = tick_end - timedelta(days=1)
                logger.info(f"Fetching tick data for {contract} (last day only)")
                ticks = await client.get_historical_tick_data(
                    contract,
                    exchange,
                    tick_start,
                    tick_end
                )
                await save_historical_data(
                    ticks, 
                    symbol_root, 
                    'ticks', 
                    tick_start, 
                    tick_end
                )
                
            except Exception as e:
                logger.error(f"Error fetching historical data for {contract}: {e}")
    
    except Exception as e:
        logger.error(f"Error in historical data collection: {e}")

async def main():
    try:
        # Get credentials from config
        config = get_chicago_gateway_config()
        
        # Create Rithmic client
        client = RithmicClient(
            user=config['rithmic']['user'],
            password=config['rithmic']['password'],
            system_name=config['rithmic']['system_name'],
            app_name=config['rithmic']['app_name'],
            app_version=config['rithmic']['app_version'],
            gateway=config['rithmic']['gateway']  # Use Chicago gateway from config
        )
        
        # Connect to Rithmic
        logger.info("Connecting to Rithmic...")
        await client.connect()
        
        # Ask user for symbols and time range
        symbols_input = input("Enter symbol roots separated by commas (default: ES,NQ): ")
        days_input = input("Enter number of days of historical data to fetch (default: 30): ")
        
        symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
        if not symbols:
            symbols = ['ES', 'NQ']
        
        days = 30
        if days_input.strip() and days_input.isdigit():
            days = int(days_input)
        
        logger.info(f"Fetching {days} days of historical data for {', '.join(symbols)}")
        
        # Fetch historical data
        await fetch_historical_data(client, symbols, days)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Disconnect from Rithmic
        if 'client' in locals() and client:
            logger.info("Disconnecting from Rithmic...")
            await client.disconnect()
            logger.info("Disconnected")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Unhandled exception: {e}")