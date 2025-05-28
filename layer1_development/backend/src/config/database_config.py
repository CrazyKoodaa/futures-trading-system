"""
Database configuration module for the futures trading system.

This module provides the DatabaseConfig class for handling database connection settings.
"""

import os
from typing import Dict, Any, Optional

from . import get_database_config


class DatabaseConfig:
    """Database configuration handler"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config:
            self.config = config
        else:
            self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from config module and environment variables"""
        # Get configuration from YAML files
        yaml_config = get_database_config()

        # Default configuration with environment variable fallbacks
        default_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "trading_db"),
            "username": os.getenv("POSTGRES_USER", "trading_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "myData4Tr4ding42!"),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "echo": os.getenv("DB_ECHO", "False").lower() == "true",
        }

        # Convert YAML config keys to match our expected format
        if "database" in yaml_config:
            # Extract database section if it exists
            db_section = yaml_config["database"]
        else:
            db_section = yaml_config

        # Map YAML keys to our config keys
        key_mapping = {
            "host": "host",
            "port": "port",
            "name": "database",
            "user": "username",
            "password": "password",
        }

        # Update config with values from YAML
        for yaml_key, config_key in key_mapping.items():
            if yaml_key in db_section:
                default_config[config_key] = db_section[yaml_key]

        # Add TimescaleDB specific configuration if available
        if "timescaledb" in yaml_config:
            default_config["timescaledb"] = yaml_config["timescaledb"]

        return default_config

    def get_sync_url(self) -> str:
        """Get synchronous database URL for SQLAlchemy"""
        from urllib.parse import quote_plus

        password = quote_plus(self.config["password"])
        return f"postgresql://{self.config['username']}:{password}@{self.config['host']}:{self.config['port']}/{self.config['database']}"

    def get_async_url(self) -> str:
        """Get asynchronous database URL for SQLAlchemy"""
        from urllib.parse import quote_plus

        password = quote_plus(self.config["password"])
        return f"postgresql+asyncpg://{self.config['username']}:{password}@{self.config['host']}:{self.config['port']}/{self.config['database']}"

    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for asyncpg"""
        return {
            "host": self.config["host"],
            "port": self.config["port"],
            "user": self.config["username"],
            "password": self.config["password"],
            "database": self.config["database"],
        }
