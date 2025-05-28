"""
Configuration and Utility Functions for Enhanced Rithmic Admin Tool
Handles configuration management, validation, and common utilities
"""

import os
import logging
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger("rithmic_admin.config")

class AdminConfig:
    """Configuration manager for the admin tool"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "admin_config.yaml"
        self.config = self._load_default_config()
        self.load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'display': {
                'mode': 'auto',  # auto, rich, simple
                'refresh_rate': 10,
                'show_performance': False,
                'color_scheme': 'default'
            },
            'keyboard': {
                'enabled': True,
                'navigation_keys': True,
                'shortcuts': True
            },
            'rithmic': {
                'connection_timeout': 30,
                'retry_attempts': 3,
                'heartbeat_interval': 15,
                'default_exchange': 'CME',
                'preferred_symbols': ['NQ', 'ES', 'YM', 'RTY']
            },
            'database': {
                'connection_timeout': 30,
                'bulk_insert_size': 1000,
                'verify_data': True
            },
            'downloads': {
                'default_days': 7,
                'chunk_size_hours': 6,
                'max_retries': 3,
                'delay_between_chunks': 0.1,
                'parallel_downloads': False
            },
            'logging': {
                'level': 'INFO',
                'file': 'rithmic_admin.log',
                'max_size_mb': 10,
                'backup_count': 3
            }
        }
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                        file_config = yaml.safe_load(f)
                    else:
                        file_config = json.load(f)
                
                # Merge with defaults
                self._merge_config(self.config, file_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.info("No config file found, using defaults")
                self.save_config()
        except Exception as e:
            logger.warning(f"Error loading config: {e}, using defaults")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def _merge_config(self, default: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'display.refresh_rate')"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate display settings
        display_mode = self.get('display.mode')
        if display_mode not in ['auto', 'rich', 'simple']:
            issues.append(f"Invalid display mode: {display_mode}")
        
        refresh_rate = self.get('display.refresh_rate')
        if not isinstance(refresh_rate, int) or refresh_rate < 1 or refresh_rate > 60:
            issues.append(f"Invalid refresh rate: {refresh_rate}")
        
        # Validate download settings
        default_days = self.get('downloads.default_days')
        if not isinstance(default_days, int) or default_days < 1:
            issues.append(f"Invalid default days: {default_days}")
        
        chunk_size = self.get('downloads.chunk_size_hours')
        if not isinstance(chunk_size, (int, float)) or chunk_size <= 0:
            issues.append(f"Invalid chunk size: {chunk_size}")
        
        return issues

class InstrumentDatabase:
    """Database of instrument specifications and metadata"""
    
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
            'trading_hours': '23:00-22:00',
            'margin_day': 14000,
            'margin_overnight': 14000
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
            'trading_hours': '23:00-22:00',
            'margin_day': 12000,
            'margin_overnight': 12000
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
            'trading_hours': '23:00-22:00',
            'margin_day': 7000,
            'margin_overnight': 7000
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
            'trading_hours': '23:00-22:00',
            'margin_day': 9000,
            'margin_overnight': 9000
        },
        'CL': {
            'full_name': 'Crude Oil',
            'tick_size': 0.01,
            'point_value': 1000.0,
            'currency': 'USD',
            'exchange': 'NYMEX',
            'exchange_code': 'XNYM',
            'product_code': 'CL',
            'months': ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'],
            'trading_hours': '23:00-22:00',
            'margin_day': 4000,
            'margin_overnight': 4000
        },
        'GC': {
            'full_name': 'Gold',
            'tick_size': 0.10,
            'point_value': 100.0,
            'currency': 'USD',
            'exchange': 'COMEX',
            'exchange_code': 'XCOM',
            'product_code': 'GC',
            'months': ['G', 'J', 'M', 'Q', 'V', 'Z'],
            'trading_hours': '23:00-22:00',
            'margin_day': 8000,
            'margin_overnight': 8000
        }
    }
    
    MONTH_CODES = {
        'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
        'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12
    }
    
    MONTH_NAMES = {
        'F': 'January', 'G': 'February', 'H': 'March', 'J': 'April',
        'K': 'May', 'M': 'June', 'N': 'July', 'Q': 'August',
        'U': 'September', 'V': 'October', 'X': 'November', 'Z': 'December'
    }
    
    @classmethod
    def get_instrument_info(cls, symbol: str) -> Optional[Dict[str, Any]]:
        """Get instrument information"""
        return cls.INSTRUMENT_SPECS.get(symbol.upper())
    
    @classmethod
    def get_all_symbols(cls) -> List[str]:
        """Get list of all available symbols"""
        return list(cls.INSTRUMENT_SPECS.keys())
    
    @classmethod
    def get_symbols_by_exchange(cls, exchange: str) -> List[str]:
        """Get symbols by exchange"""
        return [
            symbol for symbol, info in cls.INSTRUMENT_SPECS.items()
            if info['exchange'].upper() == exchange.upper()
        ]
    
    @classmethod
    def parse_contract(cls, contract: str) -> Optional[Dict[str, Any]]:
        """Parse contract string (e.g., 'NQH24') into components"""
        if len(contract) < 4:
            return None
        
        # Extract symbol (letters at the beginning)
        symbol = ''
        for i, char in enumerate(contract):
            if char.isalpha():
                symbol += char
            else:
                break
        
        if not symbol:
            return None
        
        # Extract month and year
        remaining = contract[len(symbol):]
        if len(remaining) < 2:
            return None
        
        month_letter = remaining[0].upper()
        year_suffix = remaining[1:]
        
        if month_letter not in cls.MONTH_CODES:
            return None
        
        try:
            year_num = int(year_suffix)
            # Convert 2-digit year to 4-digit
            if year_num < 50:
                full_year = 2000 + year_num
            else:
                full_year = 1900 + year_num
        except ValueError:
            return None
        
        return {
            'symbol': symbol,
            'month_letter': month_letter,
            'month_number': cls.MONTH_CODES[month_letter],
            'month_name': cls.MONTH_NAMES[month_letter],
            'year': full_year,
            'contract': contract
        }
    
    @classmethod
    def generate_contract_list(cls, symbol: str, start_date: datetime, months_ahead: int = 6) -> List[str]:
        """Generate list of contracts for a symbol"""
        contracts = []
        instrument_info = cls.get_instrument_info(symbol)
        
        if not instrument_info:
            return contracts
        
        valid_months = instrument_info['months']
        current_date = start_date
        
        for _ in range(months_ahead * 2):  # Generate extra to ensure we have enough
            year_suffix = str(current_date.year)[-2:]
            month_number = current_date.month
            
            # Find the month letter for this month
            month_letter = None
            for letter, num in cls.MONTH_CODES.items():
                if num == month_number and letter in valid_months:
                    month_letter = letter
                    break
            
            if month_letter:
                contract = f"{symbol}{month_letter}{year_suffix}"
                if contract not in contracts:
                    contracts.append(contract)
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return contracts[:months_ahead]

class UtilityFunctions:
    """Collection of utility functions"""
    
    @staticmethod
    def format_number(num: float, decimals: int = 2) -> str:
        """Format number with thousands separators"""
        if num >= 1_000_000:
            return f"{num/1_000_000:.{decimals}f}M"
        elif num >= 1_000:
            return f"{num/1_000:.{decimals}f}K"
        else:
            return f"{num:,.{decimals}f}"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    @staticmethod
    def format_bytes(bytes_count: int) -> str:
        """Format bytes in human-readable format"""
        bytes_float = float(bytes_count)  # Convert to float for division
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_float < 1024:
                return f"{bytes_float:.1f} {unit}"
            bytes_float /= 1024
        return f"{bytes_float:.1f} PB"
    
    @staticmethod
    def calculate_market_hours(symbol: str, date: datetime) -> Tuple[datetime, datetime]:
        """Calculate market open/close times for a symbol on a given date"""
        instrument_info = InstrumentDatabase.get_instrument_info(symbol)
        if not instrument_info:
            # Default hours
            return date.replace(hour=9, minute=0), date.replace(hour=16, minute=0)
        
        trading_hours = instrument_info.get('trading_hours', '09:00-16:00')
        
        # Parse trading hours (simplified)
        if '-' in trading_hours:
            start_time, end_time = trading_hours.split('-')
            start_hour, start_min = map(int, start_time.split(':'))
            end_hour, end_min = map(int, end_time.split(':'))
            
            market_open = date.replace(hour=start_hour, minute=start_min)
            market_close = date.replace(hour=end_hour, minute=end_min)
            
            # Handle overnight sessions
            if end_hour < start_hour:
                market_close += timedelta(days=1)
            
            return market_open, market_close
        
        # Default fallback
        return date.replace(hour=9, minute=0), date.replace(hour=16, minute=0)
    
    @staticmethod
    def is_trading_day(date: datetime) -> bool:
        """Check if a date is a trading day (simplified)"""
        # Monday = 0, Sunday = 6
        weekday = date.weekday()
        
        # Skip weekends
        if weekday >= 5:  # Saturday or Sunday
            return False
        
        # TODO: Add holiday checking
        return True
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate if a symbol is supported"""
        return symbol.upper() in InstrumentDatabase.get_all_symbols()
    
    @staticmethod
    def validate_exchange(exchange: str) -> bool:
        """Validate if an exchange is supported"""
        valid_exchanges = {'CME', 'CBOT', 'NYMEX', 'COMEX', 'ICE'}
        return exchange.upper() in valid_exchanges
    
    @staticmethod
    def safe_float(value, default: float = 0.0) -> float:
        """Safely convert value to float"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value, default: int = 0) -> int:
        """Safely convert value to int"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def create_directory(path: str) -> bool:
        """Create directory if it doesn't exist"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except (OSError, FileNotFoundError):
            return 0

class ErrorHandler:
    """Centralized error handling and recovery"""
    
    def __init__(self):
        self.error_counts = {}
        self.recovery_strategies = {}
    
    def register_recovery_strategy(self, error_type: str, strategy_func):
        """Register a recovery strategy for an error type"""
        self.recovery_strategies[error_type] = strategy_func
    
    async def handle_error(self, error: Exception, context: str = "") -> bool:
        """Handle an error and attempt recovery"""
        error_type = type(error).__name__
        
        # Track error frequency
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log the error
        logger.error(f"Error in {context}: {error_type} - {str(error)}")
        
        # Attempt recovery if strategy exists
        if error_type in self.recovery_strategies:
            try:
                recovery_func = self.recovery_strategies[error_type]
                success = await recovery_func(error, context)
                if success:
                    logger.info(f"Successfully recovered from {error_type}")
                    return True
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed for {error_type}: {recovery_error}")
        
        return False
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_counts.copy()
    
    def reset_error_counts(self):
        """Reset error counters"""
        self.error_counts.clear()

class SessionManager:
    """Manages session state and persistence"""
    
    def __init__(self, session_file: str = "admin_session.json"):
        self.session_file = session_file
        self.session_data = {
            'last_symbols': [],
            'last_exchange': 'CME',
            'preferred_settings': {},
            'session_history': [],
            'timestamps': {
                'created': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
        }
        self.load_session()
    
    def load_session(self):
        """Load session data from file"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    saved_data = json.load(f)
                    self.session_data.update(saved_data)
                logger.info("Session data loaded")
        except Exception as e:
            logger.warning(f"Error loading session: {e}")
    
    def save_session(self):
        """Save session data to file"""
        try:
            self.session_data['timestamps']['last_updated'] = datetime.now().isoformat()
            with open(self.session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    def update_symbols(self, symbols: List[str]):
        """Update last used symbols"""
        self.session_data['last_symbols'] = symbols
        self.save_session()
    
    def update_exchange(self, exchange: str):
        """Update last used exchange"""
        self.session_data['last_exchange'] = exchange
        self.save_session()
    
    def add_to_history(self, action: str, details: Dict[str, Any]):
        """Add action to session history"""
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        self.session_data['session_history'].append(history_entry)
        
        # Keep only last 100 entries
        if len(self.session_data['session_history']) > 100:
            self.session_data['session_history'] = self.session_data['session_history'][-100:]
        
        self.save_session()
    
    def get_last_symbols(self) -> List[str]:
        """Get last used symbols"""
        return self.session_data.get('last_symbols', [])
    
    def get_last_exchange(self) -> str:
        """Get last used exchange"""
        return self.session_data.get('last_exchange', 'CME')
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        return {
            'created': self.session_data['timestamps']['created'],
            'last_updated': self.session_data['timestamps']['last_updated'],
            'history_count': len(self.session_data['session_history']),
            'last_symbols': self.session_data['last_symbols'],
            'last_exchange': self.session_data['last_exchange']
        }

class DataValidator:
    """Validates data integrity and quality"""
    
    @staticmethod
    def validate_ohlc_data(open_price: float, high: float, low: float, close: float) -> Tuple[bool, List[str]]:
        """Validate OHLC data consistency"""
        errors = []
        
        # Check if all prices are positive
        if any(price <= 0 for price in [open_price, high, low, close]):
            errors.append("All prices must be positive")
        
        # Check high is highest
        if high < max(open_price, low, close):
            errors.append("High price must be >= open, low, and close")
        
        # Check low is lowest
        if low > min(open_price, high, close):
            errors.append("Low price must be <= open, high, and close")
        
        # Check reasonable price ranges (no more than 50% difference)
        prices = [open_price, high, low, close]
        price_range = max(prices) - min(prices)
        avg_price = sum(prices) / len(prices)
        
        if price_range / avg_price > 0.5:  # 50% range
            errors.append("Price range seems unusually large")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_volume_data(volume: int, tick_count: int) -> Tuple[bool, List[str]]:
        """Validate volume and tick data"""
        errors = []
        
        if volume < 0:
            errors.append("Volume cannot be negative")
        
        if tick_count < 0:
            errors.append("Tick count cannot be negative")
        
        if tick_count > volume and volume > 0:
            errors.append("Tick count should not exceed volume for most instruments")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_timestamp(timestamp: datetime, tolerance_hours: int = 24) -> Tuple[bool, List[str]]:
        """Validate timestamp is reasonable"""
        errors = []
        now = datetime.now()
        
        # Check if timestamp is too far in the future
        if timestamp > now + timedelta(hours=tolerance_hours):
            errors.append(f"Timestamp is too far in the future: {timestamp}")
        
        # Check if timestamp is too far in the past (more than 10 years)
        if timestamp < now - timedelta(days=365*10):
            errors.append(f"Timestamp is too far in the past: {timestamp}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_symbol_contract(symbol: str, contract: str) -> Tuple[bool, List[str]]:
        """Validate symbol and contract consistency"""
        errors = []
        
        if not symbol or not symbol.isalpha():
            errors.append("Symbol must contain only letters")
        
        if not contract:
            errors.append("Contract cannot be empty")
        
        # Parse contract and check if it starts with symbol
        if contract and symbol and not contract.upper().startswith(symbol.upper()):
            errors.append(f"Contract {contract} should start with symbol {symbol}")
        
        # Validate symbol exists in our database
        if symbol and not UtilityFunctions.validate_symbol(symbol):
            errors.append(f"Unknown symbol: {symbol}")
        
        return len(errors) == 0, errors

class PerformanceMonitor:
    """Monitors application performance"""
    
    def __init__(self):
        self.metrics = {
            'operation_times': {},
            'memory_usage': [],
            'error_rates': {},
            'api_call_times': [],
            'database_query_times': []
        }
        self.start_time = datetime.now()
    
    def record_operation_time(self, operation: str, duration: float):
        """Record time taken for an operation"""
        if operation not in self.metrics['operation_times']:
            self.metrics['operation_times'][operation] = []
        
        self.metrics['operation_times'][operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self.metrics['operation_times'][operation]) > 100:
            self.metrics['operation_times'][operation] = self.metrics['operation_times'][operation][-100:]
    
    def record_api_call(self, duration: float):
        """Record API call duration"""
        self.metrics['api_call_times'].append(duration)
        if len(self.metrics['api_call_times']) > 1000:
            self.metrics['api_call_times'] = self.metrics['api_call_times'][-1000:]
    
    def record_db_query(self, duration: float):
        """Record database query duration"""
        self.metrics['database_query_times'].append(duration)
        if len(self.metrics['database_query_times']) > 1000:
            self.metrics['database_query_times'] = self.metrics['database_query_times'][-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'operation_stats': {},
            'api_stats': {},
            'db_stats': {}
        }
        
        # Operation statistics
        for operation, times in self.metrics['operation_times'].items():
            if times:
                summary['operation_stats'][operation] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
        
        # API call statistics
        if self.metrics['api_call_times']:
            api_times = self.metrics['api_call_times']
            summary['api_stats'] = {
                'count': len(api_times),
                'avg_time': sum(api_times) / len(api_times),
                'min_time': min(api_times),
                'max_time': max(api_times)
            }
        
        # Database statistics
        if self.metrics['database_query_times']:
            db_times = self.metrics['database_query_times']
            summary['db_stats'] = {
                'count': len(db_times),
                'avg_time': sum(db_times) / len(db_times),
                'min_time': min(db_times),
                'max_time': max(db_times)
            }
        
        return summary
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        self.metrics = {
            'operation_times': {},
            'memory_usage': [],
            'error_rates': {},
            'api_call_times': [],
            'database_query_times': []
        }
        self.start_time = datetime.now()

# Context manager for operation timing
class TimedOperation:
    """Context manager for timing operations"""
    
    def __init__(self, performance_monitor: PerformanceMonitor, operation_name: str):
        self.monitor = performance_monitor
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.monitor.record_operation_time(self.operation_name, duration)

# Global instances (can be imported and used across modules)
default_config = AdminConfig()
error_handler = ErrorHandler()
session_manager = SessionManager()
performance_monitor = PerformanceMonitor()

def get_admin_config() -> AdminConfig:
    """Get the global admin configuration"""
    return default_config

def get_error_handler() -> ErrorHandler:
    """Get the global error handler"""
    return error_handler

def get_session_manager() -> SessionManager:
    """Get the global session manager"""
    return session_manager

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor"""
    return performance_monitor