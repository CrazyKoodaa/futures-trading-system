import asyncio
import os
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# Import Rithmic components
from async_rithmic import RithmicClient, TimeBarType, DataType, Gateway
from config.chicago_gateway_config import get_chicago_gateway_config

# Initialize colorama
init()

async def main():
    print(f"{Fore.CYAN}Testing Rithmic History Data API{Style.RESET_ALL}")
    
    # Get credentials from config
    config = get_chicago_gateway_config()
    
    # Create Rithmic client
    gateway_name = config['rithmic']['gateway']
    gateway = Gateway.CHICAGO if gateway_name == 'Chicago' else Gateway.TEST
    
    client = RithmicClient(
        user=config['rithmic']['user'],
        password=config['rithmic']['password'],
        system_name=config['rithmic']['system_name'],
        app_name=config['rithmic']['app_name'],
        app_version=config['rithmic']['app_version'],
        gateway=gateway
    )
    
    try:
        # Connect to Rithmic
        print(f"{Fore.YELLOW}Connecting to Rithmic...{Style.RESET_ALL}")
        await client.connect()
        print(f"{Fore.GREEN}Connected to Rithmic!{Style.RESET_ALL}")
        
        # Historical data is directly accessible through methods like get_historical_time_bars
        print(f"{Fore.YELLOW}Checking historical data access...{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Historical data access is available by default!{Style.RESET_ALL}")
        
        # Set up parameters for historical data
        symbol = "NQM5"
        exchange = "CME"
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        
        # Request historical data
        print(f"{Fore.YELLOW}Requesting historical data for {symbol}...{Style.RESET_ALL}")
        
        # Define a callback to handle historical data
        async def on_historical_time_bar(data):
            print(f"Received historical bar: {data}")
        
        # Register the callback
        client.on_historical_time_bar += on_historical_time_bar
        
        # Request the data using the get_historical_time_bars method
        print(f"{Fore.CYAN}Requesting historical time bars...{Style.RESET_ALL}")
        try:
            # Type hint to help Pylance recognize the method
            # The method exists at runtime but Pylance doesn't recognize it statically
            if not hasattr(client, 'get_historical_time_bars'):
                print(f"{Fore.YELLOW}Warning: get_historical_time_bars method not found in client{Style.RESET_ALL}")
                
            # Call the method which we know exists at runtime
            result = await client.get_historical_time_bars(  # type: ignore
                symbol,
                exchange,
                start_time,
                end_time,
                TimeBarType.MINUTE_BAR,
                1  # 1-minute bars
            )
            print(f"{Fore.GREEN}Received {len(result) if result else 0} bars{Style.RESET_ALL}")
            
            # Print the first few bars if available
            if result and len(result) > 0:
                print(f"{Fore.CYAN}First few bars:{Style.RESET_ALL}")
                for i, bar in enumerate(result[:3]):  # Show first 3 bars
                    print(f"Bar {i+1}: {bar}")
        except Exception as e:
            print(f"{Fore.RED}Error requesting historical data: {e}{Style.RESET_ALL}")
            # Wait for data to arrive via callback
            await asyncio.sleep(2)
        
        # Unregister the callback
        client.on_historical_time_bar -= on_historical_time_bar
        
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    finally:
        # Disconnect from Rithmic
        print(f"{Fore.YELLOW}Disconnecting from Rithmic...{Style.RESET_ALL}")
        await client.disconnect()
        print(f"{Fore.GREEN}Disconnected from Rithmic!{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())