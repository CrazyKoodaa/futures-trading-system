"""
Main configuration file for the futures trading system
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paper Trading Configuration (Development)
PAPER_TRADING_CONFIG = {
    'rithmic': {
        # Your Rithmic login credentials
        'user': os.getenv('RITHMIC_USER', 'your_username_here'),
        'password': os.getenv('RITHMIC_PASSWORD', 'your_password_here'),
        
        # System name assigned by Rithmic
        'system_name': os.getenv('RITHMIC_SYSTEM_NAME', 'YourSystemName'),
        
        # Paper trading server (free)
        'server_name': os.getenv('RITHMIC_SERVER_NAME', 'Rithmic Paper Trading'),
        
        # Optional application info
        'app_name': 'NQ-ES Trading Analyzer',
        'app_version': '1.0.0',
        
        # Connection settings
        'connection_timeout': 30,
        'heartbeat_interval': 30
    },
    
    # Trading configuration
    'symbols': ['NQ', 'ES'],
    'timeframes': ['1m', '5m', '15m'],
    
    # Data collection settings
    'collection': {
        'max_history_years': 5,
        'batch_size': 1000,
        'delay_between_requests': 0.1,  # 100ms between requests
        'max_retry_attempts': 5
    }
}

# Live Trading Configuration (Production)
LIVE_TRADING_CONFIG = {
    'rithmic': {
        'user': os.getenv('RITHMIC_LIVE_USER', 'live_username_here'),
        'password': os.getenv('RITHMIC_LIVE_PASSWORD', 'live_password_here'),
        'system_name': os.getenv('RITHMIC_LIVE_SYSTEM_NAME', 'ProductionSystemName'),
        'server_name': os.getenv('RITHMIC_LIVE_SERVER_NAME', 'Rithmic Live'),
        'app_name': 'Professional Trading System',
        'app_version': '2.1.0'
    },
    
    'symbols': ['NQ', 'ES'],
    'collection': {
        'max_history_years': 10,  # More history for live trading
        'delay_between_requests': 0.05,  # Faster for live
        'batch_size': 2000
    }
}

# Function to get configuration based on environment
def get_config(environment='paper'):
    """
    Get configuration for specified environment
    
    Args:
        environment: 'paper' or 'live'
        
    Returns:
        dict: Configuration dictionary
    """
    if environment == 'paper':
        return PAPER_TRADING_CONFIG
    elif environment == 'live':
        return LIVE_TRADING_CONFIG
    else:
        raise ValueError(f"Unknown environment: {environment}")