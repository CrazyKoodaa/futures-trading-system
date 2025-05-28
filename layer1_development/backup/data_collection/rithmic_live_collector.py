# rithmic_live_collector.py
"""
Script to collect live data from Rithmic
"""
import asyncio
import logging
from datetime import datetime, timedelta
from config.chicago_gateway_config import get_chicago_gateway_config
# Import the base components
from async_rithmic import TimeBarType, DataType, LastTradePresenceBits, BestBidOfferPresenceBits
from async_rithmic import ReconnectionSettings, RetrySettings
# Import our extended RithmicClient
from admin_rithmic import RithmicClient

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# For more detailed logs from async_rithmic
# logging.getLogger("rithmic").setLevel(logging.DEBUG)

async def handle_tick_data(data: dict):
    """Callback for tick data"""
    if data["data_type"] == DataType.LAST_TRADE:
        if data["presence_bits"] & LastTradePresenceBits.LAST_TRADE:
            logger.info(f"TRADE: {data['symbol']} @ {data['price']} x {data['size']}")
    
    elif data["data_type"] == DataType.BBO:
        if data["presence_bits"] & BestBidOfferPresenceBits.BID:
            logger.debug(f"BID: {data['symbol']} @ {data['bid_price']} x {data['bid_size']}")
        elif data["presence_bits"] & BestBidOfferPresenceBits.ASK:
            logger.debug(f"ASK: {data['symbol']} @ {data['ask_price']} x {data['ask_size']}")

async def handle_time_bar(data: dict):
    """Callback for time bar data"""
    logger.info(f"BAR: {data['symbol']} - O:{data['open']} H:{data['high']} L:{data['low']} C:{data['close']} V:{data['volume']}")

async def on_connected(plant_type: str):
    """Callback when connected to a plant"""
    logger.info(f"✅ Connected to {plant_type} plant")

async def on_disconnected(plant_type: str):
    """Callback when disconnected from a plant"""
    logger.warning(f"❌ Disconnected from {plant_type} plant")

async def collect_live_data(client, symbols=['ES', 'NQ']):
    """Collect live market data for specified symbols"""
    try:
        # Get front month contracts for each symbol
        contracts = []
        # Import the utility function
        from admin_rithmic import get_front_month_contract
        for symbol in symbols:
            try:
                contract = await get_front_month_contract(client, symbol, "CME")
                contracts.append((contract, "CME"))
                logger.info(f"Front month contract for {symbol}: {contract}")
            except Exception as e:
                logger.error(f"Error getting front month contract for {symbol}: {e}")
        
        if not contracts:
            logger.error("No valid contracts found")
            return
        
        # Subscribe to market data for each contract
        for contract, exchange in contracts:
            # Subscribe to tick data
            logger.info(f"Subscribing to tick data for {contract}")
            data_type = DataType.LAST_TRADE | DataType.BBO
            await client.subscribe_to_market_data(contract, exchange, data_type)
            
            # Subscribe to time bars (1-minute bars)
            logger.info(f"Subscribing to 1-minute bars for {contract}")
            await client.subscribe_to_time_bar_data(
                contract, exchange, TimeBarType.MINUTE_BAR, 1
            )
        
        # Keep the collection running
        while True:
            await asyncio.sleep(60)
            logger.info(f"Still collecting data for {', '.join([c[0] for c in contracts])}")
            
    except Exception as e:
        logger.error(f"Error in data collection: {e}")
    finally:
        # Unsubscribe from all data
        for contract, exchange in contracts:
            try:
                data_type = DataType.LAST_TRADE | DataType.BBO
                await client.unsubscribe_from_market_data(contract, exchange, data_type)
                await client.unsubscribe_from_time_bar_data(
                    contract, exchange, TimeBarType.MINUTE_BAR, 1
                )
                logger.info(f"Unsubscribed from {contract}")
            except Exception as e:
                logger.error(f"Error unsubscribing from {contract}: {e}")

async def fetch_historical_data(client, symbols=['ES', 'NQ']):
    """Fetch historical data for specified symbols"""
    try:
        # Get front month contracts for each symbol
        contracts = []
        # Import the utility function
        from admin_rithmic import get_front_month_contract
        for symbol in symbols:
            try:
                contract = await get_front_month_contract(client, symbol, "CME")
                contracts.append((contract, "CME"))
                logger.info(f"Front month contract for {symbol}: {contract}")
            except Exception as e:
                logger.error(f"Error getting front month contract for {symbol}: {e}")
        
        if not contracts:
            logger.error("No valid contracts found")
            return
        
        # Set time range for historical data (last 24 hours)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        
        # Fetch historical data for each contract
        for contract, exchange in contracts:
            try:
                # Fetch 1-minute bars
                logger.info(f"Fetching 1-minute bars for {contract} from {start_time} to {end_time}")
                bars = await client.get_historical_time_bars(
                    contract,
                    exchange,
                    start_time,
                    end_time,
                    TimeBarType.MINUTE_BAR,
                    1
                )
                logger.info(f"Received {len(bars)} 1-minute bars for {contract}")
                
                # Fetch tick data (limited to 1 hour to avoid too much data)
                tick_end = end_time
                tick_start = tick_end - timedelta(hours=1)
                logger.info(f"Fetching tick data for {contract} from {tick_start} to {tick_end}")
                ticks = await client.get_historical_tick_data(
                    contract,
                    exchange,
                    tick_start,
                    tick_end
                )
                logger.info(f"Received {len(ticks)} ticks for {contract}")
                
            except Exception as e:
                logger.error(f"Error fetching historical data for {contract}: {e}")
    
    except Exception as e:
        logger.error(f"Error in historical data collection: {e}")

async def main():
    try:
        # Get credentials from config
        config = get_chicago_gateway_config()
        
        # Configure reconnection settings
        reconnection = ReconnectionSettings(
            max_retries=None,  # retry forever
            backoff_type="exponential",
            interval=2,
            max_delay=60,
            jitter_range=(0.5, 2.0)
        )
        
        # Configure retry settings
        retry = RetrySettings(
            max_retries=3,
            timeout=30.0,
            jitter_range=(0.5, 2.0)
        )
        
        # Create Rithmic client
        client = RithmicClient(
            user=config['rithmic']['user'],
            password=config['rithmic']['password'],
            system_name=config['rithmic']['system_name'],
            app_name=config['rithmic']['app_name'],
            app_version=config['rithmic']['app_version'],
            gateway=config['rithmic']['gateway'],  # Use Chicago gateway from config
            reconnection_settings=reconnection,
            retry_settings=retry
        )
        
        # Register event handlers
        client.on_connected += on_connected
        client.on_disconnected += on_disconnected
        client.on_tick += handle_tick_data
        client.on_time_bar += handle_time_bar
        
        # Connect to Rithmic
        logger.info("Connecting to Rithmic...")
        await client.connect()
        
        # Ask user what they want to do
        print("\n=== Rithmic Data Collection ===")
        print("1. Collect live market data")
        print("2. Fetch historical data")
        print("3. Both live and historical data")
        choice = input("Enter your choice (1-3): ")
        
        try:
            if choice == '1':
                await collect_live_data(client)
            elif choice == '2':
                await fetch_historical_data(client)
            elif choice == '3':
                await fetch_historical_data(client)
                await collect_live_data(client)
            else:
                logger.error("Invalid choice")
        except KeyboardInterrupt:
            logger.info("Data collection stopped by user")
        
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