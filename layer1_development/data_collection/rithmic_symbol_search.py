# rithmic_symbol_search.py
"""
Utility script to search for symbols and retrieve front month contracts from Rithmic
"""
import asyncio
import logging
from config.chicago_gateway_config import get_chicago_gateway_config
# Import the base components
from async_rithmic import InstrumentType
# Import our extended RithmicClient
from admin_rithmic import RithmicClient

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def search_symbols(client, search_term, instrument_type=None, exchange=None):
    """
    Search for symbols matching the search term
    
    Args:
        client: RithmicClient instance
        search_term: String to search for
        instrument_type: Optional filter by instrument type
        exchange: Optional filter by exchange
        
    Returns:
        List of matching symbols
    """
    try:
        results = await client.search_symbols(
            search_term, 
            instrument_type=instrument_type, 
            exchange=exchange
        )
        
        if not results:
            logger.info(f"No symbols found matching '{search_term}'")
            return []
            
        logger.info(f"Found {len(results)} symbols matching '{search_term}'")
        return results
    except Exception as e:
        logger.error(f"Error searching for symbols: {e}")
        return []

async def list_exchanges(client):
    """
    List all available exchanges
    
    Args:
        client: RithmicClient instance
        
    Returns:
        List of exchanges
    """
    try:
        exchanges = await client.list_exchanges()
        
        if not exchanges:
            logger.info("No exchanges found")
            return []
            
        # Filter to only show exchanges you're entitled to access
        entitled_exchanges = [ex for ex in exchanges if ex.entitlement_flag == 1]
        logger.info(f"Found {len(entitled_exchanges)} exchanges you can access")
        
        return entitled_exchanges
    except Exception as e:
        logger.error(f"Error listing exchanges: {e}")
        return []

async def get_front_month_contracts(client, symbols, exchange="CME"):
    """
    Get front month contracts for a list of symbols
    
    Args:
        client: RithmicClient instance
        symbols: List of symbol roots (e.g., ['ES', 'NQ'])
        exchange: Exchange to use
        
    Returns:
        Dictionary mapping symbol roots to front month contracts
    """
    results = {}
    
    for symbol in symbols:
        try:
            # Use the utility function instead of the method
            from admin_rithmic import get_front_month_contract
            contract = await get_front_month_contract(client, symbol, exchange)
            logger.info(f"Front month contract for {symbol}: {contract}")
            results[symbol] = contract
        except Exception as e:
            logger.error(f"Error getting front month contract for {symbol}: {e}")
    
    return results

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
        
        # Menu for user
        while True:
            print("\n=== Rithmic Symbol Search ===")
            print("1. List available exchanges")
            print("2. Search for symbols")
            print("3. Get front month contracts")
            print("4. Exit")
            
            choice = input("Enter your choice (1-4): ")
            
            if choice == '1':
                exchanges = await list_exchanges(client)
                if exchanges:
                    print("\nAvailable Exchanges:")
                    for ex in exchanges:
                        print(f"- {ex.exchange}")
            
            elif choice == '2':
                search_term = input("Enter search term: ")
                exchange = input("Enter exchange (or leave blank for all): ")
                instrument_type_input = input("Enter instrument type (1=Future, 2=Option, blank=All): ")
                
                instrument_type = None
                if instrument_type_input == '1':
                    instrument_type = InstrumentType.FUTURE
                elif instrument_type_input == '2':
                    instrument_type = InstrumentType.OPTION
                
                results = await search_symbols(
                    client, 
                    search_term, 
                    instrument_type=instrument_type,
                    exchange=exchange if exchange else None
                )
                
                if results:
                    print("\nSearch Results:")
                    for i, result in enumerate(results, 1):
                        print(f"{i}. Symbol: {result.symbol}")
                        print(f"   Exchange: {result.exchange}")
                        print(f"   Name: {result.symbol_name}")
                        print(f"   Product Code: {result.product_code}")
                        print(f"   Type: {result.instrument_type}")
                        print(f"   Expiration: {result.expiration_date}")
                        print()
            
            elif choice == '3':
                symbols_input = input("Enter symbol roots separated by commas (e.g., ES,NQ): ")
                exchange = input("Enter exchange (default: CME): ")
                
                symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
                if not symbols:
                    print("No valid symbols entered")
                    continue
                
                contracts = await get_front_month_contracts(
                    client, 
                    symbols, 
                    exchange=exchange if exchange else "CME"
                )
                
                if contracts:
                    print("\nFront Month Contracts:")
                    for symbol, contract in contracts.items():
                        print(f"{symbol}: {contract}")
            
            elif choice == '4':
                break
            
            else:
                print("Invalid choice. Please try again.")
        
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