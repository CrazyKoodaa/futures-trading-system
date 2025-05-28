"""
Trading configuration module for the futures trading system.

This module provides functions to get trading-specific configuration.
"""

import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Import base configuration functions
from . import get_config as get_base_config, get_trading_environment

# Load environment variables
load_dotenv()


def get_trading_config() -> Dict[str, Any]:
    """
    Get trading configuration based on the current environment.

    Returns:
        Dict containing trading configuration
    """
    # Get current environment
    env = get_trading_environment()

    # Get base configuration
    base_config = get_base_config()

    # Default trading configuration
    default_config = {
        "symbols": ["NQ", "ES"],
        "timeframes": ["1m", "5m", "15m"],
        "collection": {
            "max_history_years": 5 if env == "development" else 10,
            "batch_size": 1000 if env == "development" else 2000,
            "delay_between_requests": 0.1 if env == "development" else 0.05,
            "max_retry_attempts": 5,
        },
    }

    # Override with values from environment-specific config
    if "trading" in base_config:
        trading_config = base_config["trading"]

        # Update symbols if available
        if "instruments" in trading_config:
            default_config["symbols"] = trading_config["instruments"]

        # Update timeframes if available
        if "timeframes" in trading_config:
            default_config["timeframes"] = trading_config["timeframes"]

        # Update collection settings if available
        if "collection" in trading_config:
            for key, value in trading_config["collection"].items():
                default_config["collection"][key] = value

    return default_config


def get_rithmic_credentials() -> Dict[str, str]:
    """
    Get Rithmic API credentials based on the current environment.

    Returns:
        Dict containing Rithmic credentials
    """
    # Get current environment
    env = get_trading_environment()

    # Get base configuration
    base_config = get_base_config()

    # Environment-specific prefixes
    prefix = "RITHMIC_LIVE_" if env == "production" else "RITHMIC_"

    # Default credentials
    credentials = {
        "user": os.getenv(f"{prefix}USER", "your_username_here"),
        "password": os.getenv(f"{prefix}PASSWORD", "your_password_here"),
        "system_name": os.getenv(f"{prefix}SYSTEM_NAME", "YourSystemName"),
        "server_name": os.getenv(
            f"{prefix}SERVER_NAME",
            "Rithmic Live" if env == "production" else "Rithmic Paper Trading",
        ),
        "app_name": "Futures Trading System",
        "app_version": "1.0.0",
    }

    # Override with values from configuration
    if "rithmic" in base_config:
        rithmic_config = base_config["rithmic"]
        for key in [
            "user",
            "password",
            "system_name",
            "server_name",
            "app_name",
            "app_version",
        ]:
            if key in rithmic_config:
                credentials[key] = rithmic_config[key]

    return credentials


def get_symbols() -> List[str]:
    """
    Get list of trading symbols.

    Returns:
        List of symbol strings
    """
    return get_trading_config()["symbols"]


def get_timeframes() -> List[str]:
    """
    Get list of timeframes.

    Returns:
        List of timeframe strings
    """
    return get_trading_config()["timeframes"]
