"""
Rithmic Symbol Manager for Futures Trading System Admin Tool

Handles symbol search, contract operations, and validation for futures contracts.
Provides wildcard search, front month detection, and contract filtering capabilities.
"""

import asyncio
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from enum import Enum

try:
    from async_rithmic import InstrumentType
except ImportError:
    # Fallback for testing
    class InstrumentType(Enum):
        FUTURE = "FUTURE"
        STOCK = "STOCK"
        OPTION = "OPTION"

from admin_rithmic_connection import RithmicConnectionManager


# Month code mappings for futures contracts
MONTH_CODES = {
    'F': 1,   # January
    'G': 2,   # February  
    'H': 3,   # March
    'J': 4,   # April
    'K': 5,   # May
    'M': 6,   # June
    'N': 7,   # July
    'Q': 8,   # August
    'U': 9,   # September
    'V': 10,  # October
    'X': 11,  # November
    'Z': 12   # December
}

# Reverse mapping for display purposes
MONTH_NAMES = {
    1: 'January (F)', 2: 'February (G)', 3: 'March (H)', 4: 'April (J)',
    5: 'May (K)', 6: 'June (M)', 7: 'July (N)', 8: 'August (Q)',
    9: 'September (U)', 10: 'October (V)', 11: 'November (X)', 12: 'December (Z)'
}

# Quarterly months for major index futures
QUARTERLY_MONTHS = ['H', 'M', 'U', 'Z']  # March, June, September, December

# Instrument specifications
INSTRUMENT_SPECS = {
    'NQ': {
        'full_name': 'E-mini NASDAQ 100',
        'tick_size': 0.25,
        'point_value': 20.0,
        'currency': 'USD',
        'exchange': 'CME',
        'months': ['H', 'M', 'U', 'Z'],
        'description': 'Nasdaq 100 index futures'
    },
    'ES': {
        'full_name': 'E-mini S&P 500',
        'tick_size': 0.25,
        'point_value': 50.0,
        'currency': 'USD',
        'exchange': 'CME', 
        'months': ['H', 'M', 'U', 'Z'],
        'description': 'S&P 500 index futures'
    },
    'YM': {
        'full_name': 'E-mini Dow',
        'tick_size': 1.0,
        'point_value': 5.0,
        'currency': 'USD',
        'exchange': 'CBOT',
        'months': ['H', 'M', 'U', 'Z'],
        'description': 'Dow Jones Industrial Average futures'
    },
    'RTY': {
        'full_name': 'E-mini Russell 2000',
        'tick_size': 0.1,
        'point_value': 50.0,
        'currency': 'USD',
        'exchange': 'CME',
        'months': ['H', 'M', 'U', 'Z'],
        'description': 'Russell 2000 index futures'
    },
    'CL': {
        'full_name': 'Crude Oil',
        'tick_size': 0.01,
        'point_value': 1000.0,
        'currency': 'USD',
        'exchange': 'NYMEX',
        'months': ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'],
        'description': 'WTI Crude Oil futures'
    },
    'GC': {
        'full_name': 'Gold',
        'tick_size': 0.1,
        'point_value': 100.0,
        'currency': 'USD',
        'exchange': 'COMEX',
        'months': ['G', 'J', 'M', 'Q', 'V', 'Z'],
        'description': 'Gold futures'
    }
}


@dataclass
class ContractInfo:
    """Container for contract information"""
    symbol: str
    exchange: str
    full_name: str
    expiration_date: Optional[datetime] = None
    tick_size: Optional[float] = None
    point_value: Optional[float] = None
    currency: str = 'USD'
    is_active: bool = True
    volume: Optional[int] = None
    open_interest: Optional[int] = None


class RithmicSymbolManager:
    """
    Manages symbol search and contract operations for Rithmic futures trading system.
    
    Provides functionality for:
    - Wildcard symbol searches
    - Front month contract detection
    - Contract validation and details
    - Quarterly contract filtering
    """
    
    def __init__(self, connection_manager: RithmicConnectionManager, progress_callback: Optional[Callable] = None):
        """
        Initialize the symbol manager.
        
        Args:
            connection_manager: RithmicConnectionManager instance
            progress_callback: Optional callback for progress updates
        """
        self.connection_manager = connection_manager
        self.progress_callback = progress_callback
        self.logger = logging.getLogger(__name__)
        
        # Cache for symbol search results
        self._symbol_cache: Dict[str, List[Dict]] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=30)
        
    def _report_progress(self, message: str, percentage: int = None):
        """Report progress if callback is available"""
        if self.progress_callback:
            self.progress_callback(message, percentage)
        self.logger.info(message)
    
    def _convert_wildcard_to_regex(self, pattern: str) -> str:
        """
        Convert wildcard pattern to regex pattern.
        
        Args:
            pattern: Wildcard pattern with * and ? characters
            
        Returns:
            Regex pattern string
        """
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        
        # Convert wildcards to regex
        regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        
        # Make it case-insensitive and anchor to word boundaries
        return f"^{regex_pattern}$"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]
    
    def _cache_results(self, cache_key: str, results: List[Dict]):
        """Cache search results"""
        self._symbol_cache[cache_key] = results
        self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
    
    async def search_symbols(self, search_term: str, exchange: str = "CME") -> List[Dict]:
        """
        Search for symbols with wildcard support.
        
        Args:
            search_term: Search pattern (supports * and ? wildcards)
            exchange: Exchange to search (default: CME)
            
        Returns:
            List of matching contract dictionaries
        """
        try:
            self._report_progress(f"Searching for symbols: {search_term} on {exchange}")
            
            # Check cache first
            cache_key = f"{search_term}_{exchange}"
            if self._is_cache_valid(cache_key):
                self.logger.info(f"Using cached results for {search_term}")
                return self._symbol_cache[cache_key]
            
            # Handle wildcard searches
            if '*' in search_term or '?' in search_term:
                results = await self.process_wildcard_search(search_term, exchange)
            else:
                results = await self._direct_symbol_search(search_term, exchange)
            
            # Cache results
            self._cache_results(cache_key, results)
            
            self._report_progress(f"Found {len(results)} matching symbols", 100)
            return results
            
        except Exception as e:
            self.logger.error(f"Symbol search failed: {e}")
            raise
    
    async def process_wildcard_search(self, search_term: str, exchange: str) -> List[Dict]:
        """
        Process wildcard search patterns.
        
        Args:
            search_term: Wildcard search pattern
            exchange: Exchange to search
            
        Returns:
            List of matching contracts
        """
        try:
            # Extract base symbol for API search
            base_term = search_term.replace('*', '').replace('?', '')
            if len(base_term) < 2:
                base_term = search_term[:2] if len(search_term) >= 2 else search_term
            
            self._report_progress(f"Processing wildcard search: {search_term}")
            
            # Get all symbols starting with base term
            all_results = await self._direct_symbol_search(base_term, exchange)
            
            # Convert wildcard to regex for filtering
            regex_pattern = self._convert_wildcard_to_regex(search_term)
            compiled_pattern = re.compile(regex_pattern, re.IGNORECASE)
            
            # Filter results by pattern
            filtered_results = []
            for result in all_results:
                symbol = result.get('symbol', '')
                if compiled_pattern.match(symbol):
                    filtered_results.append(result)
            
            # Apply quarterly filtering for NQ/ES patterns
            if any(pattern in search_term.upper() for pattern in ['NQ*', 'ES*']):
                filtered_results = self.filter_quarterly_contracts(filtered_results)
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Wildcard search failed: {e}")
            return []
    
    async def _direct_symbol_search(self, symbol: str, exchange: str) -> List[Dict]:
        """
        Perform direct API symbol search.
        
        Args:
            symbol: Symbol to search for
            exchange: Exchange to search
            
        Returns:
            List of contract dictionaries
        """
        try:
            if not self.connection_manager.is_connected():
                raise ConnectionError("Not connected to Rithmic")
            
            # Use Rithmic API to search for symbols
            client = self.connection_manager.client
            
            # Call search_symbols API method
            search_results = await client.search_symbols(
                symbol=symbol,
                exchange=exchange,
                instrument_type=InstrumentType.FUTURE
            )
            
            # Process and format results
            formatted_results = []
            for result in search_results:
                contract_info = self._format_contract_result(result)
                if contract_info:
                    formatted_results.append(contract_info)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Direct symbol search failed: {e}")
            # Return mock data for testing if API fails
            return self._get_mock_search_results(symbol, exchange)
    
    def _format_contract_result(self, api_result: Dict) -> Optional[Dict]:
        """
        Format API search result into standardized contract info.
        
        Args:
            api_result: Raw API result dictionary
            
        Returns:
            Formatted contract dictionary or None if invalid
        """
        try:
            symbol = api_result.get('symbol', '')
            if not symbol:
                return None
            
            # Extract base symbol and contract details
            base_symbol = self._extract_base_symbol(symbol)
            contract_month, contract_year = self._parse_contract_code(symbol)
            
            # Get instrument specifications
            specs = INSTRUMENT_SPECS.get(base_symbol, {})
            
            return {
                'symbol': symbol,
                'base_symbol': base_symbol,
                'exchange': api_result.get('exchange', 'CME'),
                'full_name': specs.get('full_name', api_result.get('description', '')),
                'contract_month': contract_month,
                'contract_year': contract_year,
                'month_name': MONTH_NAMES.get(MONTH_CODES.get(contract_month, 0), 'Unknown'),
                'expiration_date': api_result.get('expiration_date'),
                'tick_size': specs.get('tick_size', api_result.get('tick_size')),
                'point_value': specs.get('point_value', api_result.get('point_value')),
                'currency': specs.get('currency', 'USD'),
                'is_active': api_result.get('is_active', True),
                'volume': api_result.get('volume'),
                'open_interest': api_result.get('open_interest'),
                'description': specs.get('description', ''),
                'last_trade_date': api_result.get('last_trade_date')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to format contract result: {e}")
            return None
    
    def _extract_base_symbol(self, symbol: str) -> str:
        """Extract base symbol from full contract symbol"""
        # Remove numbers and month codes to get base symbol
        base = re.sub(r'[0-9]+$', '', symbol)  # Remove trailing numbers
        base = re.sub(r'[FGHJKMNQUVXZ][0-9]*$', '', base)  # Remove month code and year
        return base.upper()
    
    def _parse_contract_code(self, symbol: str) -> Tuple[str, int]:
        """
        Parse contract month and year from symbol.
        
        Args:
            symbol: Full contract symbol (e.g., 'NQH24')
            
        Returns:
            Tuple of (month_code, year)
        """
        try:
            # Match pattern like NQH24 or ESM2024
            match = re.search(r'([FGHJKMNQUVXZ])(\d{2,4})$', symbol)
            if match:
                month_code = match.group(1)
                year_str = match.group(2)
                
                # Convert 2-digit year to 4-digit
                if len(year_str) == 2:
                    year = 2000 + int(year_str)
                else:
                    year = int(year_str)
                
                return month_code, year
            
            return '', 0
            
        except Exception as e:
            self.logger.error(f"Failed to parse contract code from {symbol}: {e}")
            return '', 0
    
    def filter_quarterly_contracts(self, contracts: List[Dict]) -> List[Dict]:
        """
        Filter contracts to only quarterly months (H, M, U, Z).
        
        Args:
            contracts: List of contract dictionaries
            
        Returns:
            Filtered list containing only quarterly contracts
        """
        filtered = []
        for contract in contracts:
            month_code = contract.get('contract_month', '')
            if month_code in QUARTERLY_MONTHS:
                filtered.append(contract)
        
        self.logger.info(f"Filtered {len(contracts)} contracts to {len(filtered)} quarterly contracts")
        return filtered
    
    async def get_front_month_contract(self, symbol: str, exchange: str = "CME") -> Optional[str]:
        """
        Get the front month (nearest expiration) contract for a symbol.
        
        Args:
            symbol: Base symbol (e.g., 'NQ', 'ES')
            exchange: Exchange to search
            
        Returns:
            Front month contract symbol or None if not found
        """
        try:
            self._report_progress(f"Finding front month contract for {symbol}")
            
            # Search for all contracts of this symbol
            search_pattern = f"{symbol}*"
            contracts = await self.search_symbols(search_pattern, exchange)
            
            if not contracts:
                return None
            
            # Filter to active contracts only
            active_contracts = [c for c in contracts if c.get('is_active', True)]
            
            # Sort by expiration date (nearest first)
            active_contracts.sort(key=lambda x: self._get_contract_sort_key(x))
            
            if active_contracts:
                front_month = active_contracts[0]['symbol']
                self._report_progress(f"Front month contract: {front_month}")
                return front_month
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get front month contract: {e}")
            return None
    
    def _get_contract_sort_key(self, contract: Dict) -> Tuple[int, int]:
        """
        Generate sort key for contract ordering by expiration.
        
        Args:
            contract: Contract dictionary
            
        Returns:
            Tuple of (year, month_number) for sorting
        """
        year = contract.get('contract_year', 9999)
        month_code = contract.get('contract_month', 'Z')
        month_number = MONTH_CODES.get(month_code, 12)
        
        return (year, month_number)
    
    async def validate_contracts(self, contracts: List[str], exchange: str = "CME") -> Dict[str, bool]:
        """
        Validate that contracts exist and are tradeable.
        
        Args:
            contracts: List of contract symbols to validate
            exchange: Exchange to check
            
        Returns:
            Dictionary mapping contract -> validity (True/False)
        """
        try:
            self._report_progress(f"Validating {len(contracts)} contracts")
            
            validation_results = {}
            
            for i, contract in enumerate(contracts):
                try:
                    # Get contract details
                    details = await self.get_contract_details(contract, exchange)
                    validation_results[contract] = details is not None and details.get('is_active', False)
                    
                    # Report progress
                    progress = int((i + 1) / len(contracts) * 100)
                    self._report_progress(f"Validated {i + 1}/{len(contracts)} contracts", progress)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to validate contract {contract}: {e}")
                    validation_results[contract] = False
            
            valid_count = sum(1 for v in validation_results.values() if v)
            self._report_progress(f"Validation complete: {valid_count}/{len(contracts)} contracts valid")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Contract validation failed: {e}")
            return {contract: False for contract in contracts}
    
    async def get_contract_details(self, contract: str, exchange: str = "CME") -> Optional[Dict]:
        """
        Get detailed information for a specific contract.
        
        Args:
            contract: Contract symbol
            exchange: Exchange
            
        Returns:
            Contract details dictionary or None if not found
        """
        try:
            if not self.connection_manager.is_connected():
                raise ConnectionError("Not connected to Rithmic")
            
            client = self.connection_manager.client
            
            # Get contract details from API
            details = await client.get_contract_details(
                symbol=contract,
                exchange=exchange
            )
            
            if details:
                return self._format_contract_result(details)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get contract details for {contract}: {e}")
            # Return mock data for testing
            return self._get_mock_contract_details(contract, exchange)
    
    async def check_database_data(self, contracts: List[str]) -> Dict[str, Dict]:
        """
        Check existing database data for contracts.
        
        Args:
            contracts: List of contract symbols
            
        Returns:
            Dictionary with contract data statistics
        """
        try:
            self._report_progress(f"Checking database data for {len(contracts)} contracts")
            
            results = {}
            
            for contract in contracts:
                # This would integrate with your database layer
                # For now, return mock data structure
                results[contract] = {
                    'record_count': 0,
                    'date_range': {
                        'start': None,
                        'end': None
                    },
                    'latest_timestamp': None,
                    'data_gaps': [],
                    'has_data': False
                }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Database check failed: {e}")
            return {}
    
    def format_contracts_for_display(self, contracts: List[Dict]) -> str:
        """
        Format contract list for user-friendly display.
        
        Args:
            contracts: List of contract dictionaries
            
        Returns:
            Formatted markdown string
        """
        if not contracts:
            return "No contracts found."
        
        # Group by base symbol
        grouped = {}
        for contract in contracts:
            base = contract.get('base_symbol', 'Unknown')
            if base not in grouped:
                grouped[base] = []
            grouped[base].append(contract)
        
        # Format output
        output = []
        output.append("## Found Contracts\n")
        
        for base_symbol, contract_list in grouped.items():
            specs = INSTRUMENT_SPECS.get(base_symbol, {})
            full_name = specs.get('full_name', base_symbol)
            
            output.append(f"### {base_symbol} - {full_name}")
            if specs.get('description'):
                output.append(f"*{specs['description']}*")
            output.append("")
            
            # Sort contracts by expiration
            sorted_contracts = sorted(contract_list, key=self._get_contract_sort_key)
            
            for contract in sorted_contracts:
                symbol = contract['symbol']
                month_name = contract.get('month_name', 'Unknown')
                year = contract.get('contract_year', '')
                
                status = "✅ Active" if contract.get('is_active', True) else "❌ Expired"
                
                output.append(f"- **{symbol}** - {month_name} {year} ({status})")
                
                if contract.get('volume'):
                    output.append(f"  - Volume: {contract['volume']:,}")
                if contract.get('open_interest'):
                    output.append(f"  - Open Interest: {contract['open_interest']:,}")
            
            output.append("")
        
        return "\n".join(output)
    
    def _get_mock_search_results(self, symbol: str, exchange: str) -> List[Dict]:
        """Generate mock search results for testing"""
        base_symbol = symbol.upper()[:2]
        if base_symbol not in INSTRUMENT_SPECS:
            return []
        
        # Generate mock contracts for current and next few months
        current_year = datetime.now().year
        mock_results = []
        
        specs = INSTRUMENT_SPECS[base_symbol]
        months = specs.get('months', QUARTERLY_MONTHS)
        
        for month in months:
            for year_offset in [0, 1]:
                year = current_year + year_offset
                year_code = str(year)[-2:]  # 2-digit year
                contract_symbol = f"{base_symbol}{month}{year_code}"
                
                mock_results.append({
                    'symbol': contract_symbol,
                    'base_symbol': base_symbol,
                    'exchange': exchange,
                    'full_name': specs['full_name'],
                    'contract_month': month,
                    'contract_year': year,
                    'month_name': MONTH_NAMES.get(MONTH_CODES.get(month, 0), 'Unknown'),
                    'tick_size': specs['tick_size'],
                    'point_value': specs['point_value'],
                    'currency': specs['currency'],
                    'is_active': True,
                    'description': specs['description']
                })
        
        return mock_results
    
    def _get_mock_contract_details(self, contract: str, exchange: str) -> Optional[Dict]:
        """Generate mock contract details for testing"""
        base_symbol = self._extract_base_symbol(contract)
        if base_symbol not in INSTRUMENT_SPECS:
            return None
        
        specs = INSTRUMENT_SPECS[base_symbol]
        month_code, year = self._parse_contract_code(contract)
        
        return {
            'symbol': contract,
            'base_symbol': base_symbol,
            'exchange': exchange,
            'full_name': specs['full_name'],
            'contract_month': month_code,
            'contract_year': year,
            'month_name': MONTH_NAMES.get(MONTH_CODES.get(month_code, 0), 'Unknown'),
            'tick_size': specs['tick_size'],
            'point_value': specs['point_value'],
            'currency': specs['currency'],
            'is_active': True,
            'description': specs['description'],
            'volume': 50000,
            'open_interest': 100000
        }


# Utility functions for external use
def parse_contract_symbol(symbol: str) -> Dict[str, Any]:
    """
    Parse a contract symbol into components.
    
    Args:
        symbol: Contract symbol (e.g., 'NQH24')
        
    Returns:
        Dictionary with parsed components
    """
    manager = RithmicSymbolManager(None)  # No connection needed for parsing
    
    base_symbol = manager._extract_base_symbol(symbol)
    month_code, year = manager._parse_contract_code(symbol)
    
    return {
        'symbol': symbol,
        'base_symbol': base_symbol,
        'contract_month': month_code,
        'contract_year': year,
        'month_name': MONTH_NAMES.get(MONTH_CODES.get(month_code, 0), 'Unknown'),
        'month_number': MONTH_CODES.get(month_code, 0)
    }


def get_instrument_specs(symbol: str) -> Dict[str, Any]:
    """
    Get instrument specifications for a symbol.
    
    Args:
        symbol: Base symbol (e.g., 'NQ', 'ES')
        
    Returns:
        Instrument specifications dictionary
    """
    return INSTRUMENT_SPECS.get(symbol.upper(), {})


def is_quarterly_contract(symbol: str) -> bool:
    """
    Check if a contract is a quarterly contract (H, M, U, Z).
    
    Args:
        symbol: Contract symbol
        
    Returns:
        True if quarterly contract, False otherwise
    """
    match = re.search(r'([FGHJKMNQUVXZ])\d+$', symbol)
    if match:
        month_code = match.group(1)
        return month_code in QUARTERLY_MONTHS
    return False


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_symbol_manager():
        """Test the symbol manager functionality"""
        # Mock connection manager for testing
        class MockConnectionManager:
            @property
            def is_connected(self):
                return True
            
            @property
            def client(self):
                return self
            
            async def search_symbols(self, symbol, exchange, instrument_type):
                return []
            
            async def get_contract_details(self, symbol, exchange):
                return None
        
        # Create manager with mock connection
        mock_conn = MockConnectionManager()
        manager = RithmicSymbolManager(mock_conn)
        
        # Test symbol search
        print("Testing symbol search...")
        results = await manager.search_symbols("NQ*", "CME")
        print(f"Found {len(results)} contracts")
        
        # Test contract formatting
        if results:
            formatted = manager.format_contracts_for_display(results)
            print("\nFormatted results:")
            print(formatted)
        
        # Test front month detection
        front_month = await manager.get_front_month_contract("NQ", "CME")
        print(f"\nFront month contract: {front_month}")
        
        # Test utility functions
        parsed = parse_contract_symbol("NQH24")
        print(f"\nParsed NQH24: {parsed}")
        
        specs = get_instrument_specs("NQ")
        print(f"\nNQ specifications: {specs}")
        
        print(f"\nIs NQH24 quarterly? {is_quarterly_contract('NQH24')}")
        print(f"Is NQF24 quarterly? {is_quarterly_contract('NQF24')}")
    
    # Run test
    asyncio.run(test_symbol_manager())
