# data_collection/async_rithmic_tick_collector.py
"""
Enhanced AsyncRithmicCollector for second-based tick data collection
Specifically configured for Rithmic Paper Trading via Gateway Chicago
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, AsyncGenerator, Union
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import json
import time
from pathlib import Path
import sqlite3
from contextlib import asynccontextmanager

try:
    import async_rithmic
    from async_rithmic import RithmicClient, LoginParams, TickParams, HistoryParams
    from async_rithmic.client import TickData, QuoteData
except ImportError:
    logging.error("async_rithmic not installed. Install with: pip install async_rithmic")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TickDataPoint:
    """Individual tick data point"""
    timestamp: datetime
    symbol: str
    contract: str
    exchange: str
    price: float
    size: int
    tick_type: str  # 'trade', 'bid', 'ask'
    exchange_timestamp: Optional[datetime] = None
    sequence: Optional[int] = None

@dataclass
class AggregatedSecondData:
    """Aggregated second-based OHLCV data"""
    timestamp: datetime
    symbol: str
    contract: str
    exchange: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    tick_count: int
    vwap: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None

@dataclass
class ChicagoGatewayConfig:
    """Configuration specific to Chicago Gateway"""
    gateway_name: str = "Chicago"
    timezone: str = "America/Chicago"
    market_hours: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        'pre_market': (6, 9),    # 6:00 AM - 9:00 AM CT
        'regular': (9, 16),      # 9:00 AM - 4:00 PM CT  
        'after_hours': (16, 20)  # 4:00 PM - 8:00 PM CT
    })
    max_ticks_per_second: int = 1000
    tick_buffer_size: int = 10000

class AsyncRithmicTickCollector:
    """
    Enhanced collector for second-based tick data via Rithmic Chicago Gateway
    
    Features:
    - Real-time tick data collection
    - Second-based aggregation
    - Chicago timezone handling
    - Market hours awareness
    - High-frequency data processing
    - Direct database storage
    """
    
    # Chicago Gateway specific settings
    CHICAGO_GATEWAY_CONFIG = ChicagoGatewayConfig()
    
    # Futures contract specifications (same as before)
    MONTH_CODES = {
        'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
        'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12
    }
    
    INSTRUMENT_SPECS = {
        'NQ': {
            'full_name': 'E-mini NASDAQ 100',
            'tick_size': 0.25,
            'point_value': 20.0,
            'currency': 'USD',
            'exchange': 'CME',
            'exchange_code': 'XCME',
            'product_code': 'NQ',
            'months': ['H', 'M', 'U', 'Z'],
            'trading_hours': '23:00-22:00'  # Nearly 24/7
        },
        'ES': {
            'full_name': 'E-mini S&P 500',
            'tick_size': 0.25,
            'point_value': 50.0,
            'currency': 'USD',
            'exchange': 'CME',
            'exchange_code': 'XCME',
            'product_code': 'ES',
            'months': ['H', 'M', 'U', 'Z'],
            'trading_hours': '23:00-22:00'  # Nearly 24/7
        },
        'YM': {
            'full_name': 'E-mini Dow Jones',
            'tick_size': 1.0,
            'point_value': 5.0,
            'currency': 'USD',
            'exchange': 'CBOT',
            'exchange_code': 'XCBT',
            'product_code': 'YM',
            'months': ['H', 'M', 'U', 'Z'],
            'trading_hours': '23:00-22:00'
        },
        'RTY': {
            'full_name': 'E-mini Russell 2000',
            'tick_size': 0.10,
            'point_value': 50.0,
            'currency': 'USD',
            'exchange': 'CME',
            'exchange_code': 'XCME',
            'product_code': 'RTY',
            'months': ['H', 'M', 'U', 'Z'],
            'trading_hours': '23:00-22:00'
        }
    }
    
    def __init__(self, config: Dict):
        """
        Initialize the tick data collector
        
        Args:
            config: Configuration with Rithmic credentials and Chicago Gateway settings
        """
        self.config = config
        self.chicago_config = ChicagoGatewayConfig()
        
        # Rithmic connection for Chicago Gateway
        self.rithmic_config = config.get('rithmic', {})
        self.client: Optional[RithmicClient] = None
        self.is_connected = False
        
        # Tick data management
        self.tick_buffer: Dict[str, List[TickDataPoint]] = {}
        self.second_data_buffer: Dict[str, List[AggregatedSecondData]] = {}
        self.last_prices: Dict[str, float] = {}
        self.last_quotes: Dict[str, Tuple[float, float]] = {}  # (bid, ask)
        
        # Data processing
        self.aggregation_tasks: Dict[str, asyncio.Task] = {}
        self.is_collecting = False
        
        # Database connection (will be implemented)
        self.db_connection = None
        
        # Performance tracking
        self.stats = {
            'ticks_received': 0,
            'seconds_aggregated': 0,
            'start_time': None,
            'last_tick_time': None
        }
        
        logger.info("Initialized AsyncRithmicTickCollector for Chicago Gateway")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> bool:
        """
        Connect to Rithmic Chicago Gateway
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Rithmic Paper Trading via Chicago Gateway
            login_params = LoginParams(
                user=self.rithmic_config['user'],
                password=self.rithmic_config['password'],
                system_name=self.rithmic_config['system_name'],
                server_name="Rithmic Paper Trading",
                gateway=self.rithmic_config.get('gateway', 'Chicago'),
                app_name=self.rithmic_config.get('app_name', 'Tick Data Collector'),
                app_version=self.rithmic_config.get('app_version', '1.0.0')
            )
            
            self.client = RithmicClient()
            
            # Connect with Chicago-specific settings
            await asyncio.wait_for(
                self.client.connect(login_params),
                timeout=self.rithmic_config.get('connection_timeout', 30)
            )
            
            self.is_connected = True
            self.stats['start_time'] = datetime.now()
            
            logger.info("✅ Connected to Rithmic Chicago Gateway for Paper Trading")
            return True
            
        except asyncio.TimeoutError:
            logger.error("❌ Connection timeout to Chicago Gateway")
            return False
        except Exception as e:
            logger.error(f"❌ Connection failed to Chicago Gateway: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Rithmic and cleanup"""
        # Stop all collection tasks
        await self.stop_tick_collection()
        
        # Disconnect from Rithmic
        if self.client and self.is_connected:
            try:
                await self.client.disconnect()
                logger.info("Disconnected from Rithmic Chicago Gateway")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.client = None
                self.is_connected = False
    
    def get_chicago_time(self) -> datetime:
        """Get current Chicago time"""
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    
    def is_market_open(self, symbol: str = 'NQ') -> bool:
        """
        Check if market is open (futures trade nearly 24/7)
        
        Args:
            symbol: Futures symbol
            
        Returns:
            bool: True if market is open
        """
        chicago_time = self.get_chicago_time()
        
        # Futures markets are closed only briefly on weekends
        # Sunday 5 PM CT - Friday 4 PM CT with daily maintenance breaks
        
        weekday = chicago_time.weekday()  # 0=Monday, 6=Sunday
        hour = chicago_time.hour
        
        # Market closed Saturday 4 PM - Sunday 5 PM CT
        if weekday == 6 and hour < 17:  # Sunday before 5 PM
            return False
        if weekday == 5 and hour >= 16:  # Saturday after 4 PM
            return False
            
        # Daily maintenance break (usually 4-5 PM CT)
        if hour == 16:  # 4-5 PM CT maintenance
            return False
            
        return True
    
    async def subscribe_to_ticks(self, contracts: List[str]):
        """
        Subscribe to tick data for specified contracts
        
        Args:
            contracts: List of contract strings (e.g., ['NQZ24', 'ESZ24'])
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Rithmic")
        
        for contract in contracts:
            try:
                # Subscribe to tick data
                tick_params = TickParams(
                    symbol=contract,
                    tick_types=['trade', 'bid', 'ask'],  # All tick types
                    include_volume=True,
                    include_timestamp=True
                )
                
                await self.client.subscribe_ticks(tick_params, self._handle_tick_data)
                
                # Initialize buffers
                self.tick_buffer[contract] = []
                self.second_data_buffer[contract] = []
                
                logger.info(f"✅ Subscribed to tick data for {contract}")
                
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {contract}: {e}")
    
    async def _handle_tick_data(self, tick_data: TickData):
        """
        Handle incoming tick data from Rithmic
        
        Args:
            tick_data: Tick data from Rithmic
        """
        try:
            # Convert Rithmic tick data to our format
            tick = TickDataPoint(
                timestamp=tick_data.timestamp or datetime.now(),
                symbol=self._extract_symbol(tick_data.symbol),
                contract=tick_data.symbol,
                exchange=self._get_exchange_for_contract(tick_data.symbol),
                price=tick_data.price,
                size=tick_data.size or 0,
                tick_type=tick_data.tick_type,
                exchange_timestamp=tick_data.exchange_timestamp,
                sequence=tick_data.sequence
            )
            
            # Add to buffer
            contract = tick.contract
            if contract in self.tick_buffer:
                self.tick_buffer[contract].append(tick)
                
                # Update statistics
                self.stats['ticks_received'] += 1
                self.stats['last_tick_time'] = tick.timestamp
                
                # Update last price and quotes
                if tick.tick_type == 'trade':
                    self.last_prices[contract] = tick.price
                elif tick.tick_type == 'bid':
                    bid, ask = self.last_quotes.get(contract, (0, 0))
                    self.last_quotes[contract] = (tick.price, ask)
                elif tick.tick_type == 'ask':
                    bid, ask = self.last_quotes.get(contract, (0, 0))
                    self.last_quotes[contract] = (bid, tick.price)
                
                # Trigger aggregation if buffer is full
                if len(self.tick_buffer[contract]) >= self.chicago_config.max_ticks_per_second:
                    await self._trigger_aggregation(contract)
                    
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
    
    def _get_exchange_for_contract(self, contract: str) -> str:
        """
        Get exchange for contract
        
        Args:
            contract: Contract string (e.g., 'NQZ24')
            
        Returns:
            str: Exchange name (CME, CBOT, etc.)
        """
        symbol = self._extract_symbol(contract)
        return self.INSTRUMENT_SPECS.get(symbol, {}).get('exchange', 'CME')
    
    def _get_exchange_code_for_contract(self, contract: str) -> str:
        """
        Get exchange code for contract
        
        Args:
            contract: Contract string (e.g., 'NQZ24')
            
        Returns:
            str: Exchange code (XCME, XCBT, etc.)
        """
        symbol = self._extract_symbol(contract)
        return self.INSTRUMENT_SPECS.get(symbol, {}).get('exchange_code', 'XCME')
    
    async def _trigger_aggregation(self, contract: str):
        """Trigger second-based aggregation for contract"""
        if contract not in self.aggregation_tasks or self.aggregation_tasks[contract].done():
            self.aggregation_tasks[contract] = asyncio.create_task(
                self._aggregate_second_data(contract)
            )
    
    async def _aggregate_second_data(self, contract: str):
        """
        Aggregate tick data into second-based OHLCV bars
        
        Args:
            contract: Contract to aggregate
        """
        try:
            ticks = self.tick_buffer.get(contract, [])
            if not ticks:
                return
            
            # Group ticks by second
            second_groups = {}
            
            for tick in ticks:
                # Truncate to second
                second_timestamp = tick.timestamp.replace(microsecond=0)
                
                if second_timestamp not in second_groups:
                    second_groups[second_timestamp] = []
                second_groups[second_timestamp].append(tick)
            
            # Create second bars
            for timestamp, second_ticks in second_groups.items():
                # Filter trade ticks for OHLCV
                trade_ticks = [t for t in second_ticks if t.tick_type == 'trade']
                
                if trade_ticks:
                    prices = [t.price for t in trade_ticks]
                    volumes = [t.size for t in trade_ticks]
                    
                    # Calculate OHLCV
                    open_price = trade_ticks[0].price
                    high_price = max(prices)
                    low_price = min(prices)
                    close_price = trade_ticks[-1].price
                    total_volume = sum(volumes)
                    tick_count = len(trade_ticks)
                    
                    # Calculate VWAP
                    if total_volume > 0:
                        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume
                    else:
                        vwap = close_price
                    
                    # Get latest bid/ask
                    bid, ask = self.last_quotes.get(contract, (None, None))
                    spread = ask - bid if bid and ask else None
                    
                    # Create second bar
                    second_bar = AggregatedSecondData(
                        timestamp=timestamp,
                        symbol=self._extract_symbol(contract),
                        contract=contract,
                        exchange=self._get_exchange_for_contract(contract),
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=total_volume,
                        tick_count=tick_count,
                        vwap=vwap,
                        bid=bid,
                        ask=ask,
                        spread=spread
                    )
                    
                    # Add to buffer
                    if contract not in self.second_data_buffer:
                        self.second_data_buffer[contract] = []
                    
                    self.second_data_buffer[contract].append(second_bar)
                    self.stats['seconds_aggregated'] += 1
                    
                    # Save to database if buffer is full
                    if len(self.second_data_buffer[contract]) >= 60:  # Every minute
                        await self._save_second_data_to_db(contract)
            
            # Clear processed ticks
            self.tick_buffer[contract] = []
            
        except Exception as e:
            logger.error(f"Error aggregating second data for {contract}: {e}")
    
    async def _save_second_data_to_db(self, contract: str):
        """
        Save second-based data to TimescaleDB using SQLAlchemy models
        
        Args:
            contract: Contract to save data for
        """
        try:
            second_data = self.second_data_buffer.get(contract, [])
            if not second_data:
                return
            
            # Import SQLAlchemy models
            from shared.database.models import MarketDataSeconds, DatabaseManager
            from shared.database.connection import get_async_session
            
            # Convert to database format
            data_records = []
            for bar in second_data:
                # Get exchange code
                exchange_code = self._get_exchange_code_for_contract(contract)
                
                record = {
                    'timestamp': bar.timestamp,
                    'symbol': bar.symbol,
                    'contract': bar.contract,
                    'exchange': bar.exchange,
                    'exchange_code': exchange_code,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': bar.volume,
                    'tick_count': bar.tick_count,
                    'vwap': float(bar.vwap) if bar.vwap else None,
                    'bid': float(bar.bid) if bar.bid else None,
                    'ask': float(bar.ask) if bar.ask else None,
                    'spread': float(bar.spread) if bar.spread else None,
                    'data_quality_score': 1.0,  # Assume good quality for real-time data
                    'is_regular_hours': self.is_market_open(bar.symbol)
                }
                data_records.append(record)
            
            # Save to database using async session
            async with get_async_session() as session:
                db_manager = DatabaseManager(session)
                await db_manager.bulk_insert_market_data(data_records, MarketDataSeconds)
            
            # Clear buffer
            self.second_data_buffer[contract] = []
            
            logger.info(f"💾 Saved {len(data_records)} second bars for {contract} to TimescaleDB")
            
        except Exception as e:
            logger.error(f"Error saving second data for {contract} to database: {e}")
            # Fall back to file storage
            await self._save_to_temp_storage_fallback(contract)
    
    async def _save_to_temp_storage_fallback(self, contract: str):
        """Fallback storage when database save fails"""
        try:
            second_data = self.second_data_buffer.get(contract, [])
            if not second_data:
                return
                
            # Convert to DataFrame
            data_dict = []
            for bar in second_data:
                data_dict.append({
                    'timestamp': bar.timestamp,
                    'symbol': bar.symbol,
                    'contract': bar.contract,
                    'exchange': bar.exchange,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume,
                    'tick_count': bar.tick_count,
                    'vwap': bar.vwap,
                    'bid': bar.bid,
                    'ask': bar.ask,
                    'spread': bar.spread
                })
            
            df = pd.DataFrame(data_dict)
            
            # Create output directory
            output_dir = Path(f"data/tick_data/{contract}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as parquet with timestamp in filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = output_dir / f"seconds_{timestamp_str}.parquet"
            
            df.to_parquet(filename, index=False)
            logger.warning(f"📁 Saved to fallback storage: {filename}")
            
        except Exception as e:
            logger.error(f"Error in fallback storage for {contract}: {e}")
    
    async def save_raw_tick_to_db(self, tick: TickDataPoint):
        """
        Save individual tick to database (optional - for detailed analysis)
        
        Args:
            tick: Individual tick data point
        """
        try:
            from shared.database.models import RawTickData
            from shared.database.connection import get_async_session
            
            async with get_async_session() as session:
                raw_tick = RawTickData(
                    timestamp=tick.timestamp,
                    symbol=tick.symbol,
                    contract=tick.contract,
                    exchange=tick.exchange,
                    sequence_number=tick.sequence or int(time.time() * 1000000),  # Microsecond timestamp
                    price=float(tick.price),
                    size=tick.size,
                    tick_type=tick.tick_type,
                    exchange_timestamp=tick.exchange_timestamp
                )
                
                session.add(raw_tick)
                await session.commit()
                
        except Exception as e:
            logger.debug(f"Error saving raw tick: {e}")  # Debug level since this is optional
    
    async def start_tick_collection(self, contracts: List[str]):
        """
        Start collecting tick data for specified contracts
        
        Args:
            contracts: List of contracts to collect (e.g., ['NQZ24', 'ESZ24'])
        """
        if not self.is_connected:
            await self.connect()
        
        logger.info(f"🚀 Starting tick collection for {contracts}")
        
        # Subscribe to tick data
        await self.subscribe_to_ticks(contracts)
        
        self.is_collecting = True
        
        # Start periodic aggregation task
        asyncio.create_task(self._periodic_aggregation())
        
        logger.info("✅ Tick collection started")
    
    async def _periodic_aggregation(self):
        """Periodic aggregation task (every second)"""
        while self.is_collecting:
            try:
                # Trigger aggregation for all contracts
                for contract in self.tick_buffer.keys():
                    if self.tick_buffer[contract]:  # Only if there are ticks
                        await self._trigger_aggregation(contract)
                
                # Wait one second
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in periodic aggregation: {e}")
    
    async def stop_tick_collection(self):
        """Stop tick data collection"""
        logger.info("⏹️ Stopping tick collection")
        
        self.is_collecting = False
        
        # Cancel aggregation tasks
        for task in self.aggregation_tasks.values():
            if not task.done():
                task.cancel()
        
        # Final aggregation and save
        for contract in list(self.tick_buffer.keys()):
            await self._aggregate_second_data(contract)
            await self._save_second_data_to_db(contract)
        
        logger.info("✅ Tick collection stopped")
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        current_time = datetime.now()
        duration = (current_time - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        
        return {
            'ticks_received': self.stats['ticks_received'],
            'seconds_aggregated': self.stats['seconds_aggregated'],
            'duration_seconds': duration,
            'ticks_per_second': self.stats['ticks_received'] / duration if duration > 0 else 0,
            'last_tick_time': self.stats['last_tick_time'],
            'is_collecting': self.is_collecting,
            'active_contracts': list(self.tick_buffer.keys()),
            'buffer_sizes': {k: len(v) for k, v in self.tick_buffer.items()}
        }
    
    def generate_current_contracts(self, symbols: List[str] = None) -> List[str]:
        """Generate current active contracts"""
        if symbols is None:
            symbols = ['NQ', 'ES']
        
        contracts = []
        current_date = datetime.now()
        
        for symbol in symbols:
            # Get current and next month contracts
            for months_ahead in [0, 1, 2, 3]:  # Current + 3 months ahead
                target_date = current_date + timedelta(days=months_ahead * 30)
                
                # Find appropriate contract month
                month = target_date.month
                year = target_date.year
                
                # Find next quarterly month (Mar, Jun, Sep, Dec for NQ/ES)
                quarterly_months = [3, 6, 9, 12]
                next_quarterly = min([m for m in quarterly_months if m >= month], default=quarterly_months[0])
                
                if next_quarterly < month:
                    year += 1
                
                month_letter = self.MONTH_CODES.get(next_quarterly, 'Z')
                year_suffix = str(year)[-2:]
                
                contract = f"{symbol}{month_letter}{year_suffix}"
                if contract not in contracts:
                    contracts.append(contract)
        
        return contracts[:4]  # Limit to 4 most relevant contracts


# Configuration for Chicago Gateway
def get_chicago_gateway_config(username: str, password: str, system_name: str) -> Dict:
    """
    Get configuration for Chicago Gateway Paper Trading
    
    Args:
        username: Your Rithmic username
        password: Your Rithmic password
        system_name: Your registered system name
        
    Returns:
        Dict: Configuration for tick collector
    """
    return {
        'rithmic': {
            'user': username,
            'password': password,
            'system_name': system_name,
            'server_name': 'Rithmic Paper Trading',
            'gateway': 'Chicago',
            'app_name': 'Second-Based Data Collector',
            'app_version': '1.0.0',
            'connection_timeout': 30,
            'heartbeat_interval': 15
        },
        'symbols': ['NQ', 'ES'],
        'chicago_gateway': {
            'timezone': 'America/Chicago',
            'max_ticks_per_second': 1000,
            'tick_buffer_size': 10000,
            'save_interval_seconds': 60
        },
        'collection': {
            'tick_types': ['trade', 'bid', 'ask'],
            'include_volume': True,
            'include_quotes': True,
            'aggregation_interval': 1  # seconds
        }
    }


# Example usage
async def main():
    """Example of collecting second-based tick data"""
    
    # Your Rithmic credentials
    config = get_chicago_gateway_config(
        username="your_username",        # Replace with your username
        password="your_password",        # Replace with your password  
        system_name="your_system_name"   # Replace with your system name
    )
    
    async with AsyncRithmicTickCollector(config) as collector:
        # Get current active contracts
        contracts = collector.generate_current_contracts(['NQ', 'ES'])
        print(f"Active contracts: {contracts}")
        
        # Start collecting tick data
        await collector.start_tick_collection(contracts)
        
        # Collect for 5 minutes (for testing)
        print("🔄 Collecting tick data for 5 minutes...")
        await asyncio.sleep(300)  # 5 minutes
        
        # Stop collection
        await collector.stop_tick_collection()
        
        # Print statistics
        stats = collector.get_stats()
        print(f"📊 Collection Stats:")
        print(f"   Ticks received: {stats['ticks_received']}")
        print(f"   Seconds aggregated: {stats['seconds_aggregated']}")
        print(f"   Ticks per second: {stats['ticks_per_second']:.2f}")
        print(f"   Duration: {stats['duration_seconds']:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())