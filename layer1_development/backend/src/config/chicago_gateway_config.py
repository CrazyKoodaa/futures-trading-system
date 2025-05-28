# chicago_gateway_config.py
"""
Configuration for connecting to Rithmic via Chicago Gateway
"""

import os
from typing import Dict, Any
from . import get_config, load_yaml_config


def get_chicago_gateway_config() -> Dict[str, Any]:
    """
    Get configuration for Rithmic connection

    Returns:
        dict: Configuration dictionary for Rithmic client
    """
    # Try to load from YAML config file
    try:
        # Load environment-specific config
        env_config = get_config()
        rithmic_config = get_config("rithmic")

        # Start with default configuration
        config = {
            "rithmic": {
                "user": os.getenv("RITHMIC_USER", "ETF-177266"),
                "password": os.getenv("RITHMIC_PASSWORD", "t2bRVPUaw"),
                "system_name": os.getenv("RITHMIC_SYSTEM_NAME", "Rithmic Paper Trading"),
                "app_name": "Futures Analyzer",
                "app_version": "1.0.0",
                "gateway": "Chicago",
            },
            "use_test_gateway": False,
            "symbols": ["NQ", "ES"],
            "collection": {
                "tick_types": ["trade", "bid", "ask"],
                "include_volume": True,
                "include_quotes": True,
                "time_bar_intervals": [1, 5, 15, 60],
            },
        }

        # Override with values from config files if available
        if "rithmic" in env_config:
            for key, value in env_config["rithmic"].items():
                if key in config["rithmic"]:
                    config["rithmic"][key] = value

        # Override with values from rithmic_config.yaml if available
        if rithmic_config:
            # Update instruments/symbols if available
            if "instruments" in rithmic_config:
                config["symbols"] = list(rithmic_config["instruments"].keys())

            # Update data types if available
            if "data_types" in rithmic_config:
                config["collection"]["tick_types"] = rithmic_config["data_types"]

            # Update connection settings if available
            if "connection" in rithmic_config:
                conn_config = rithmic_config["connection"]
                if "timeout" in conn_config:
                    config["connection_timeout"] = conn_config["timeout"]
                if "heartbeat_interval" in conn_config:
                    config["heartbeat_interval"] = conn_config["heartbeat_interval"]

        return config

    except Exception as e:
        # Fallback to default configuration if loading fails
        print(f"Error loading Rithmic configuration: {e}")
        return {
            "rithmic": {
                "user": "ETF-177266",
                "password": "t2bRVPUaw",
                "system_name": "Rithmic Paper Trading",
                "app_name": "Futures Analyzer",
                "app_version": "1.0.0",
                "gateway": "Chicago",
            },
            "use_test_gateway": False,
            "symbols": ["NQ", "ES"],
            "collection": {
                "tick_types": ["trade", "bid", "ask"],
                "include_volume": True,
                "include_quotes": True,
                "time_bar_intervals": [1, 5, 15, 60],
            },
        }
