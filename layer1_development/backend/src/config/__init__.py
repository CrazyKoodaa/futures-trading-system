"""
Configuration module for the futures trading system.

This module provides functions to load configuration from YAML files.
"""

import os
from typing import Dict, Any, Optional, Union, List
import yaml

# Default configuration paths
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV = os.getenv("TRADING_ENV", "development")
DEFAULT_CONFIG_FILES = {
    "database": os.path.join(CONFIG_DIR, "database.yaml"),
    "development": os.path.join(CONFIG_DIR, "development.yaml"),
    "production": os.path.join(CONFIG_DIR, "production.yaml"),
    "rithmic": os.path.join(CONFIG_DIR, "rithmic_config.yaml"),
}


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dict containing the configuration
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except (IOError, yaml.YAMLError) as e:
        print(f"Error loading config file {file_path}: {e}")
        return {}


def get_database_config() -> Dict[str, Any]:
    """
    Get database configuration from YAML file and environment variables.

    Returns:
        Dict containing database configuration
    """
    # Load base configuration from YAML
    db_config = load_yaml_config(DEFAULT_CONFIG_FILES["database"])

    # Load environment-specific database configuration
    env_config = load_yaml_config(DEFAULT_CONFIG_FILES[DEFAULT_ENV])
    if "database" in env_config:
        # Override with environment-specific settings
        return {**db_config, **env_config["database"]}

    return db_config


def get_config(config_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration by type.

    Args:
        config_type: Type of configuration to load (database, rithmic, etc.). If None, returns the environment-specific configuration.

    Returns:
        Dict containing the configuration
    """
    if config_type == "database":
        return get_database_config()
    if config_type in DEFAULT_CONFIG_FILES:
        return load_yaml_config(DEFAULT_CONFIG_FILES[config_type])
    # Load environment-specific configuration
    return load_yaml_config(DEFAULT_CONFIG_FILES[DEFAULT_ENV])


def get_trading_environment() -> str:
    """
    Get the current trading environment.

    Returns:
        String representing the current environment ('development', 'production', etc.)
    """
    return DEFAULT_ENV


def get_config_path(config_type: str) -> str:
    """
    Get the path to a specific configuration file.

    Args:
        config_type: Type of configuration file ('database', 'development', etc.)

    Returns:
        String path to the configuration file
    """
    if config_type in DEFAULT_CONFIG_FILES:
        return DEFAULT_CONFIG_FILES[config_type]
    else:
        raise ValueError(f"Unknown configuration type: {config_type}")


def get_all_config() -> Dict[str, Any]:
    """
    Get all configuration merged into a single dictionary.

    Returns:
        Dict containing all configuration
    """
    # Start with environment-specific configuration
    config = load_yaml_config(DEFAULT_CONFIG_FILES[DEFAULT_ENV])

    # Add database configuration
    db_config = get_database_config()
    if "database" not in config:
        config["database"] = {}
    config["database"].update(db_config)

    # Add rithmic configuration
    rithmic_config = load_yaml_config(DEFAULT_CONFIG_FILES["rithmic"])
    if "rithmic" not in config:
        config["rithmic"] = {}
    config["rithmic"].update(rithmic_config)

    return config
