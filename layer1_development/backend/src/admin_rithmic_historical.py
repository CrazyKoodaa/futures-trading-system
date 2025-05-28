"""
Rithmic Historical Data Manager
Handles downloading and processing historical market data from Rithmic API.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Callable, Optional, Any
import pytz
from dataclasses import dataclass
import math

try:
    from async_rithmic import TimeBarType
except ImportError:
    # Fallback enum for development
    class TimeBarType:
        SECOND_BAR = "SECOND_BAR"
        MINUTE_BAR = "MINUTE_BAR"

from admin_core_classes import DownloadProgress

# Configure logging
logger = logging.getLogger(__name__)

# Chunk configurations for different data types
CHUNK_CONFIGS = {
    'second_bars': {
        'max_chunk_hours': 6,
        'max_data_points': 9999,
        'empty_chunk_limit': 4,
        'rate_limit_delay': 0.5,  # seconds between requests
        'retry_attempts': 3
    },
    'minute_bars': {
        'max_chunk_days': 2,
        'max_data_points': 9999,
        'empty_chunk_limit': 3,
        'rate_limit_delay': 0.3,
        'retry_attempts': 3
    }
}

# Market hours configuration (US Central Time)
MARKET_HOURS = {
    'futures': {
        'start_time': time(17, 0),  # 5:00 PM CT (Sunday open)
        'end_time': time(16, 0),    # 4:00 PM CT (Friday close)
        'closed_hours': [(time(16, 0), time(17, 0))],  # Daily maintenance
        'closed_days': []  # Futures trade almost 24/7
    },
    'equity': {
        'start_time': time(8, 30),   # 8:30 AM CT
        'end_time': time(15, 0),     # 3:00 PM CT
        'closed_hours': [],
        'closed_days': [5, 6]  # Saturday, Sunday
    }
}

# Major US holidays (simplified)
MARKET_HOLIDAYS_2024_2025 = [
    datetime(2024, 1, 1),   # New Year's Day
    datetime(2024, 1, 15),  # MLK Day
    datetime(2024, 2, 19),  # Presidents Day
    datetime(2024, 5, 27),  # Memorial Day
    datetime(2024, 6, 19),  # Juneteenth
    datetime(2024, 7, 4),   # Independence Day
    datetime(2024, 9, 2),   # Labor Day
    datetime(2024, 11, 28), # Thanksgiving
    datetime(2024, 12, 25), # Christmas
    datetime(2025, 1, 1),   # New Year's Day
    datetime(2025, 1, 20),  # MLK Day
    datetime(2025, 2, 17),  # Presidents Day
    datetime(2025, 5, 26),  # Memorial Day
    datetime(2025, 6, 19),  # Juneteenth
    datetime(2025, 7, 4),   # Independence Day
    datetime(2025, 9, 1),   # Labor Day
    datetime(2025, 11, 27), # Thanksgiving
    datetime(2025, 12, 25), # Christmas
]


@dataclass
class DownloadStats:
    """Statistics for a download operation"""
    total_bars: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    empty_chunks: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    api_calls: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class RithmicHistoricalError(Exception):
    """Custom exception for historical data operations"""
    pass


class RithmicHistoricalManager:
    """
    Manages historical data downloads from Rithmic API.
    Handles chunking, progress tracking, error recovery, and data processing.
    """
    
    def __init__(self, 
                 connection_manager,
                 database_ops,
                 progress_callback: Callable = None):
        """
        Initialize the historical data manager.
        
        Args:
            connection_manager: RithmicConnectionManager instance
            database_ops: Database operations instance
            progress_callback: Optional callback for progress updates
        """
        self.connection_manager = connection_manager
        self.database_ops = database_ops
        self.progress_callback = progress_callback
        self.download_stats = {}
        self.timezone = pytz.timezone('US/Central')
        
        logger.info("RithmicHistoricalManager initialized")
    
    async def download_historical_data(self, 
                                     contracts: List[str],
                                     days: int = 7,
                                     download_seconds: bool = True,
                                     download_minutes: bool = True) -> str:
        """
        Download historical data for multiple contracts.
        
        Args:
            contracts: List of contract symbols
            days: Number of days of historical data
            download_seconds: Whether to download second bars
            download_minutes: Whether to download minute bars
            
        Returns:
            Status message summarizing the download operation
        """
        logger.info(f"Starting historical data download for {len(contracts)} contracts, {days} days")
        
        overall_start = datetime.now()
        total_operations = len(contracts) * (int(download_seconds) + int(download_minutes))
        completed_operations = 0
        
        # Calculate date range
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time = end_time - timedelta(days=days)
        
        results = []
        
        for contract in contracts:
            try:
                # Extract symbol and exchange from contract
                symbol, exchange = self._parse_contract(contract)
                
                # Initialize stats for this contract
                self.download_stats[contract] = DownloadStats(start_time=datetime.now())
                
                # Download second bars
                if download_seconds:
                    logger.info(f"Downloading second bars for {contract}")
                    second_data = await self.download_second_bars(
                        contract, exchange, start_time, end_time
                    )
                    
                    if second_data:
                        # Process and save to database
                        processed_data = self.process_bar_data(
                            second_data, symbol, contract, exchange
                        )
                        
                        success = await self.save_to_database(
                            processed_data, f"{symbol}_second_bars"
                        )
                        
                        if success:
                            self.download_stats[contract].total_bars += len(processed_data)
                            logger.info(f"Saved {len(processed_data)} second bars for {contract}")
                        else:
                            logger.error(f"Failed to save second bars for {contract}")
                    
                    completed_operations += 1
                    await self.update_download_progress(
                        contract, completed_operations, total_operations,
                        "Historical Download", "Second Bars Complete"
                    )
                
                # Download minute bars
                if download_minutes:
                    logger.info(f"Downloading minute bars for {contract}")
                    minute_data = await self.download_minute_bars(
                        contract, exchange, start_time, end_time
                    )
                    
                    if minute_data:
                        # Process and save to database
                        processed_data = self.process_bar_data(
                            minute_data, symbol, contract, exchange
                        )
                        
                        success = await self.save_to_database(
                            processed_data, f"{symbol}_minute_bars"
                        )
                        
                        if success:
                            self.download_stats[contract].total_bars += len(processed_data)
                            logger.info(f"Saved {len(processed_data)} minute bars for {contract}")
                        else:
                            logger.error(f"Failed to save minute bars for {contract}")
                    
                    completed_operations += 1
                    await self.update_download_progress(
                        contract, completed_operations, total_operations,
                        "Historical Download", "Minute Bars Complete"
                    )
                
                # Finalize stats
                self.download_stats[contract].end_time = datetime.now()
                self.download_stats[contract].duration_seconds = (
                    self.download_stats[contract].end_time - 
                    self.download_stats[contract].start_time
                ).total_seconds()
                
                results.append(f"{contract}: {self.download_stats[contract].total_bars} bars")
                
            except Exception as e:
                error_msg = f"Error downloading data for {contract}: {str(e)}"
                logger.error(error_msg)
                results.append(f"{contract}: ERROR - {str(e)}")
                
                if contract in self.download_stats:
                    self.download_stats[contract].errors.append(error_msg)
        
        # Generate summary
        total_duration = (datetime.now() - overall_start).total_seconds()
        total_bars = sum(stats.total_bars for stats in self.download_stats.values())
        
        summary = f"Historical download completed in {total_duration:.1f}s. "
        summary += f"Total bars: {total_bars}. "
        summary += f"Contracts processed: {len(results)}"
        
        logger.info(summary)
        return summary
    
    async def download_second_bars(self, 
                                 contract: str,
                                 exchange: str,
                                 start_time: datetime,
                                 end_time: datetime) -> List[Dict]:
        """
        Download second bars for a specific contract.
        
        Args:
            contract: Contract symbol
            exchange: Exchange name
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            List of bar data dictionaries
        """
        logger.info(f"Downloading second bars for {contract} from {start_time} to {end_time}")
        
        all_bars = []
        chunks = self.calculate_chunks(start_time, end_time, 'second_bars')
        config = CHUNK_CONFIGS['second_bars']
        
        for i, (chunk_start, chunk_end) in enumerate(chunks):
            # Update progress
            await self.update_download_progress(
                contract, i + 1, len(chunks),
                "Downloading Second Bars", f"Chunk {i+1}/{len(chunks)}"
            )
            
            # Skip non-market hours for efficiency
            if not self.is_likely_market_hours(chunk_start):
                logger.debug(f"Skipping chunk {i+1} - outside market hours")
                continue
            
            # Download chunk with retry logic
            chunk_bars = await self._download_chunk_with_retry(
                contract, exchange, chunk_start, chunk_end,
                TimeBarType.SECOND_BAR, 1, config
            )
            
            if chunk_bars:
                all_bars.extend(chunk_bars)
                self.download_stats[contract].successful_chunks += 1
                logger.debug(f"Downloaded {len(chunk_bars)} second bars in chunk {i+1}")
            else:
                self.download_stats[contract].empty_chunks += 1
                logger.debug(f"Empty chunk {i+1} for second bars")
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit_delay'])
        
        logger.info(f"Downloaded {len(all_bars)} total second bars for {contract}")
        return all_bars
    
    async def download_minute_bars(self,
                                 contract: str,
                                 exchange: str,
                                 start_time: datetime,
                                 end_time: datetime) -> List[Dict]:
        """
        Download minute bars for a specific contract.
        
        Args:
            contract: Contract symbol
            exchange: Exchange name
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            List of bar data dictionaries
        """
        logger.info(f"Downloading minute bars for {contract} from {start_time} to {end_time}")
        
        all_bars = []
        chunks = self.calculate_chunks(start_time, end_time, 'minute_bars')
        config = CHUNK_CONFIGS['minute_bars']
        
        for i, (chunk_start, chunk_end) in enumerate(chunks):
            # Update progress
            await self.update_download_progress(
                contract, i + 1, len(chunks),
                "Downloading Minute Bars", f"Chunk {i+1}/{len(chunks)}"
            )
            
            # Skip non-market hours for efficiency
            if not self.is_likely_market_hours(chunk_start):
                logger.debug(f"Skipping chunk {i+1} - outside market hours")
                continue
            
            # Download chunk with retry logic
            chunk_bars = await self._download_chunk_with_retry(
                contract, exchange, chunk_start, chunk_end,
                TimeBarType.MINUTE_BAR, 1, config
            )
            
            if chunk_bars:
                all_bars.extend(chunk_bars)
                self.download_stats[contract].successful_chunks += 1
                logger.debug(f"Downloaded {len(chunk_bars)} minute bars in chunk {i+1}")
            else:
                self.download_stats[contract].empty_chunks += 1
                logger.debug(f"Empty chunk {i+1} for minute bars")
            
            # Rate limiting
            await asyncio.sleep(config['rate_limit_delay'])
        
        logger.info(f"Downloaded {len(all_bars)} total minute bars for {contract}")
        return all_bars
    
    def calculate_chunks(self,
                        start_time: datetime,
                        end_time: datetime,
                        chunk_type: str) -> List[Tuple[datetime, datetime]]:
        """
        Calculate time chunks for data download.
        
        Args:
            start_time: Start datetime
            end_time: End datetime
            chunk_type: 'second_bars' or 'minute_bars'
            
        Returns:
            List of (chunk_start, chunk_end) tuples
        """
        config = CHUNK_CONFIGS.get(chunk_type, CHUNK_CONFIGS['minute_bars'])
        chunks = []
        
        current_start = start_time
        
        if chunk_type == 'second_bars':
            chunk_delta = timedelta(hours=config['max_chunk_hours'])
        else:  # minute_bars
            chunk_delta = timedelta(days=config['max_chunk_days'])
        
        while current_start < end_time:
            chunk_end = min(current_start + chunk_delta, end_time)
            chunks.append((current_start, chunk_end))
            current_start = chunk_end
        
        logger.debug(f"Created {len(chunks)} chunks for {chunk_type}")
        return chunks
    
    def is_likely_market_hours(self, dt: datetime) -> bool:
        """
        Determine if a datetime is likely during market hours.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if likely market hours, False otherwise
        """
        # Convert to US Central time
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)
        
        # Check if it's a major holiday
        date_only = dt.date()
        for holiday in MARKET_HOLIDAYS_2024_2025:
            if holiday.date() == date_only:
                return False
        
        # For futures (assume most contracts are futures)
        # Futures trade almost 24/7 except during maintenance
        weekday = dt.weekday()
        time_only = dt.time()
        
        # Weekend check (Saturday afternoon to Sunday evening)
        if weekday == 5 and time_only > time(16, 0):  # Saturday after 4 PM
            return False
        if weekday == 6 and time_only < time(17, 0):  # Sunday before 5 PM
            return False
        
        # Daily maintenance window (4 PM to 5 PM CT)
        if time(16, 0) <= time_only <= time(17, 0):
            return False
        
        return True
    
    async def update_download_progress(self,
                                     symbol: str,
                                     current_chunk: int,
                                     total_chunks: int,
                                     operation: str,
                                     timeframe: str):
        """
        Update download progress and trigger callback.
        
        Args:
            symbol: Symbol being processed
            current_chunk: Current chunk number
            total_chunks: Total number of chunks
            operation: Current operation description
            timeframe: Current timeframe being processed
        """
        progress = DownloadProgress(
            symbol=symbol,
            current_operation=operation,
            total_chunks=total_chunks,
            completed_chunks=current_chunk,
            current_timeframe=timeframe,
            start_time=datetime.now(),
            completion_percentage=round((current_chunk / total_chunks) * 100, 1)
        )
        
        if self.progress_callback:
            try:
                self.progress_callback(symbol, progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        logger.debug(f"Progress: {symbol} - {operation} - {progress.completion_percentage}%")
    
    def process_bar_data(self,
                        raw_bars: List[Dict],
                        symbol: str,
                        contract: str,
                        exchange: str) -> List[Dict]:
        """
        Process raw bar data into standardized format.
        
        Args:
            raw_bars: Raw bar data from API
            symbol: Base symbol
            contract: Full contract identifier
            exchange: Exchange name
            
        Returns:
            List of processed bar records
        """
        processed_data = []
        
        for bar in raw_bars:
            try:
                # Extract timestamp
                timestamp = bar.get('bar_end_datetime')
                if timestamp is None:
                    timestamp = bar.get('timestamp', datetime.now())
                
                # Ensure timestamp is datetime object
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # Create standardized record
                record = {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'contract': contract,
                    'exchange': exchange,
                    'exchange_code': self._get_exchange_code(exchange),
                    'open': float(bar.get('open', 0)),
                    'high': float(bar.get('high', 0)),
                    'low': float(bar.get('low', 0)),
                    'close': float(bar.get('close', 0)),
                    'volume': int(bar.get('volume', 0)),
                    'tick_count': int(bar.get('tick_count', 1)),
                    'vwap': float(bar.get('vwap', bar.get('close', 0))),
                    'data_quality_score': self._calculate_quality_score(bar),
                    'is_regular_hours': self.is_likely_market_hours(timestamp)
                }
                
                # Validate record
                if self._validate_bar_record(record):
                    processed_data.append(record)
                else:
                    logger.warning(f"Invalid bar record skipped: {bar}")
                    
            except Exception as e:
                logger.error(f"Error processing bar: {bar}, error: {e}")
                continue
        
        logger.debug(f"Processed {len(processed_data)} bars from {len(raw_bars)} raw bars")
        return processed_data
    
    async def save_to_database(self, processed_data: List[Dict], table_name: str) -> bool:
        """
        Save processed data to database.
        
        Args:
            processed_data: List of processed bar records
            table_name: Target table name
            
        Returns:
            True if successful, False otherwise
        """
        if not processed_data:
            logger.warning("No data to save to database")
            return True
        
        try:
            # Use database operations for bulk insertion
            success = await self.database_ops.bulk_insert_market_data(
                processed_data, table_name
            )
            
            if success:
                logger.info(f"Successfully saved {len(processed_data)} records to {table_name}")
                return True
            else:
                logger.error(f"Failed to save data to {table_name}")
                return False
                
        except Exception as e:
            logger.error(f"Database save error: {e}")
            return False
    
    async def _download_chunk_with_retry(self,
                                       contract: str,
                                       exchange: str,
                                       start_time: datetime,
                                       end_time: datetime,
                                       bar_type: str,
                                       interval: int,
                                       config: Dict) -> List[Dict]:
        """
        Download a chunk of data with retry logic.
        
        Args:
            contract: Contract symbol
            exchange: Exchange name
            start_time: Chunk start time
            end_time: Chunk end time
            bar_type: Type of bars to download
            interval: Bar interval
            config: Configuration for this data type
            
        Returns:
            List of bar data or empty list if failed
        """
        for attempt in range(config['retry_attempts']):
            try:
                # Increment API call counter
                if contract in self.download_stats:
                    self.download_stats[contract].api_calls += 1
                
                # Make API call
                chunk_bars = await self.connection_manager.client.get_historical_time_bars(
                    contract, exchange, start_time, end_time, bar_type, interval
                )
                
                if chunk_bars:
                    return chunk_bars
                else:
                    logger.debug(f"Empty response for {contract} chunk {start_time} to {end_time}")
                    return []
                    
            except Exception as e:
                error_msg = f"API call failed (attempt {attempt + 1}): {str(e)}"
                logger.warning(error_msg)
                
                if contract in self.download_stats:
                    self.download_stats[contract].errors.append(error_msg)
                
                if attempt < config['retry_attempts'] - 1:
                    # Exponential backoff
                    delay = config['rate_limit_delay'] * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to download chunk after {config['retry_attempts']} attempts")
                    if contract in self.download_stats:
                        self.download_stats[contract].failed_chunks += 1
        
        return []
    
    def _parse_contract(self, contract: str) -> Tuple[str, str]:
        """
        Parse contract string to extract symbol and exchange.
        
        Args:
            contract: Full contract identifier
            
        Returns:
            Tuple of (symbol, exchange)
        """
        # Handle different contract formats
        if '.' in contract:
            parts = contract.split('.')
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        # Default assumption for common futures
        if contract.startswith('ES'):
            return contract, 'CME'
        elif contract.startswith('NQ'):
            return contract, 'CME'
        elif contract.startswith('YM'):
            return contract, 'CBOT'
        elif contract.startswith('RTY'):
            return contract, 'CME'
        else:
            # Generic fallback
            return contract, 'CME'
    
    def _get_exchange_code(self, exchange: str) -> str:
        """
        Get standardized exchange code.
        
        Args:
            exchange: Exchange name
            
        Returns:
            Standardized exchange code
        """
        exchange_map = {
            'CME': 'XCME',
            'CBOT': 'XCBT',
            'NYMEX': 'XNYM',
            'COMEX': 'XCEC',
            'ICE': 'IFUS'
        }
        return exchange_map.get(exchange.upper(), exchange.upper())
    
    def _calculate_quality_score(self, bar: Dict) -> float:
        """
        Calculate data quality score for a bar.
        
        Args:
            bar: Raw bar data
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 1.0
        
        # Check for missing or zero values
        required_fields = ['open', 'high', 'low', 'close']
        for field in required_fields:
            if bar.get(field, 0) == 0:
                score -= 0.2
        
        # Check for valid OHLC relationships
        try:
            o, h, l, c = [float(bar.get(f, 0)) for f in required_fields]
            if h < max(o, c) or l > min(o, c):
                score -= 0.3
        except (ValueError, TypeError):
            score -= 0.5
        
        # Check volume
        if bar.get('volume', 0) == 0:
            score -= 0.1
        
        return max(0.0, score)
    
    def _validate_bar_record(self, record: Dict) -> bool:
        """
        Validate a processed bar record.
        
        Args:
            record: Processed bar record
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['timestamp', 'symbol', 'open', 'high', 'low', 'close']
        
        for field in required_fields:
            if field not in record or record[field] is None:
                return False
        
        # Check OHLC validity
        try:
            o, h, l, c = record['open'], record['high'], record['low'], record['close']
            if h < max(o, c) or l > min(o, c):
                return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    def get_download_statistics(self, contract: str = None) -> Dict:
        """
        Get download statistics.
        
        Args:
            contract: Specific contract or None for all
            
        Returns:
            Dictionary of statistics
        """
        if contract and contract in self.download_stats:
            return self.download_stats[contract].__dict__
        elif contract is None:
            return {k: v.__dict__ for k, v in self.download_stats.items()}
        else:
            return {}
    
    def reset_statistics(self):
        """Reset all download statistics."""
        self.download_stats.clear()
        logger.info("Download statistics reset")


# Utility functions for external use
def format_download_summary(stats: Dict) -> str:
    """
    Format download statistics into a readable summary.
    
    Args:
        stats: Statistics dictionary
        
    Returns:
        Formatted summary string
    """
    if not stats:
        return "No download statistics available"
    
    summary_lines = []
    total_bars = 0
    total_duration = 0
    total_api_calls = 0
    
    for contract, contract_stats in stats.items():
        if isinstance(contract_stats, dict):
            bars = contract_stats.get('total_bars', 0)
            duration = contract_stats.get('duration_seconds', 0)
            api_calls = contract_stats.get('api_calls', 0)
            errors = len(contract_stats.get('errors', []))
            
            total_bars += bars
            total_duration += duration
            total_api_calls += api_calls
            
            summary_lines.append(
                f"{contract}: {bars:,} bars, {duration:.1f}s, "
                f"{api_calls} API calls, {errors} errors"
            )
    
    summary = "\n".join(summary_lines)
    summary += f"\n\nTotals: {total_bars:,} bars, {total_duration:.1f}s, {total_api_calls} API calls"
    
    return summary


def is_market_open(dt: datetime = None) -> bool:
    """
    Quick check if market is likely open.
    
    Args:
        dt: Datetime to check (default: now)
        
    Returns:
        True if market likely open
    """
    if dt is None:
        dt = datetime.now()
    
    # Simple heuristic - avoid weekends and major holidays
    weekday = dt.weekday()
    if weekday >= 5:  # Saturday or Sunday
        return False
    
    # Check major holidays
    date_only = dt.date()
    for holiday in MARKET_HOLIDAYS_2024_2025:
        if holiday.date() == date_only:
            return False
    
    return True
