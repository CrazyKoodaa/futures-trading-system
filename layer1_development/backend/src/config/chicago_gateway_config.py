# chicago_gateway_config.py
"""
Configuration for connecting to Rithmic via Chicago Gateway
"""

def get_chicago_gateway_config():
    """
    Get configuration for Rithmic connection
    
    Returns:
        dict: Configuration dictionary for Rithmic client
    """
    return {
        'rithmic': {
            'user': "ETF-177266",      # Your Rithmic username
            'password': "t2bRVPUaw",   # Your Rithmic password
            'system_name': "Rithmic Paper Trading",  # Your registered system name
            'app_name': "Futures Trading System",
            'app_version': "1.0.0",
            'gateway': 'Chicago',
        },
        'use_test_gateway': False,  # Set to True to use test gateway instead of live
        'symbols': ['NQ', 'ES'],    # Default symbols to collect
        'collection': {
            'tick_types': ['trade', 'bid', 'ask'],
            'include_volume': True,
            'include_quotes': True,
            'time_bar_intervals': [1, 5, 15, 60]  # 1, 5, 15, 60 minute bars
        }
    }