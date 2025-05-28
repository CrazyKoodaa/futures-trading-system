"""
Rithmic API Connection Management for Admin Tool

This module provides connection management functionality for the Rithmic API,
including authentication, connection monitoring, automatic reconnection,
and graceful error handling.

Key Features:
- Async connection management with Chicago Gateway
- Automatic reconnection with exponential backoff
- Connection health monitoring and status tracking
- Progress reporting for UI updates
- Comprehensive error handling and recovery
- Thread-safe operations
"""

import asyncio
import logging
import time
from typing import Dict, Any, Tuple, Callable, Optional
from datetime import datetime, timedelta
import traceback

from config.chicago_gateway_config import get_chicago_gateway_config
from async_rithmic import RithmicClient, Gateway, ReconnectionSettings, RetrySettings
from admin_core_classes import SystemStatus

# Configure logging
logger = logging.getLogger(__name__)


class RithmicConnectionManager:
    """
    Manages Rithmic API connections with automatic reconnection,
    health monitoring, and comprehensive error handling.
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize the connection manager.

        Args:
            progress_callback: Optional callback for progress updates
        """
        self.progress_callback = progress_callback
        self.client: Optional[RithmicClient] = None
        self.is_connected: bool = False
        self.connection_config: Optional[Dict[str, Any]] = None
        self.last_heartbeat: Optional[datetime] = None
        self.connection_attempts: int = 0
        self.last_connection_attempt: Optional[datetime] = None
        self.connection_start_time: Optional[datetime] = None
        self.connection_errors: list = []
        self._lock = asyncio.Lock()

        # Connection monitoring settings
        self.heartbeat_interval = 30  # seconds
        self.max_connection_age = 3600  # 1 hour
        self.health_check_task: Optional[asyncio.Task] = None

    def _report_progress(self, message: str, status: str = "info"):
        """Report progress to callback if available."""
        if self.progress_callback is not None:
            try:
                self.progress_callback(message, status)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        logger.info(message)

    async def connect(self) -> Tuple[bool, str]:
        """
        Establish connection to Rithmic API.

        Returns:
            Tuple of (success: bool, message: str)
        """
        async with self._lock:
            if self.is_connected and self.client:
                return True, "**Already connected** ✅"

            self.connection_start_time = datetime.now()
            self.connection_attempts += 1
            self.last_connection_attempt = datetime.now()

            try:
                self._report_progress(
                    "🔄 **Initializing connection to Rithmic API...**"
                )

                # Load configuration
                self._report_progress("📋 Loading Chicago Gateway configuration...")
                try:
                    self.connection_config = get_chicago_gateway_config()
                except Exception as e:
                    error_msg = f"❌ **Configuration Error**: {str(e)}"
                    self.connection_errors.append(
                        {
                            "timestamp": datetime.now(),
                            "error": error_msg,
                            "type": "config",
                        }
                    )
                    return False, error_msg

                # Setup connection settings (removed invalid ReconnectionSettings and RetrySettings)
                self._report_progress("⚙️ Configuring connection settings...")

                # Create client
                self._report_progress("🏗️ Creating Rithmic client...")
                try:
                    if self.connection_config is None:
                        raise Exception("Connection configuration is not loaded")
                    
                    rithmic_config = self.connection_config.get("rithmic", {})
                    if not rithmic_config:
                        raise Exception("Rithmic configuration section not found")
                    
                    self.client = RithmicClient(
                        user=rithmic_config["user"],
                        password=rithmic_config["password"],
                        gateway=Gateway.CHICAGO,
                        system_name=rithmic_config.get(
                            "system_name", "AdminTool"
                        ),
                        app_name=rithmic_config.get("app_name", "RithmicAdmin"),
                        app_version=self.connection_config.get("app_version", "1.0.0"),
                    )
                except Exception as e:
                    error_msg = f"❌ **Client Creation Error**: {str(e)}"
                    self.connection_errors.append(
                        {
                            "timestamp": datetime.now(),
                            "error": error_msg,
                            "type": "client_creation",
                        }
                    )
                    return False, error_msg

                # Attempt connection
                self._report_progress("🔌 Connecting to Chicago Gateway...")
                try:
                    await asyncio.wait_for(self.client.connect(), timeout=30.0)

                    # Verify connection
                    if not self.client.is_connected():
                        raise Exception(
                            "Connection established but client reports not connected"
                        )

                except asyncio.TimeoutError:
                    error_msg = (
                        "❌ **Connection Timeout**: Failed to connect within 30 seconds"
                    )
                    self.connection_errors.append(
                        {
                            "timestamp": datetime.now(),
                            "error": error_msg,
                            "type": "timeout",
                        }
                    )
                    return False, error_msg

                except Exception as e:
                    error_msg = f"❌ **Connection Error**: {str(e)}"
                    self.connection_errors.append(
                        {
                            "timestamp": datetime.now(),
                            "error": error_msg,
                            "type": "connection",
                        }
                    )
                    return False, error_msg

                # Connection successful
                self.is_connected = True
                self.last_heartbeat = datetime.now()
                connection_time = (
                    datetime.now() - self.connection_start_time
                ).total_seconds()

                # Start health monitoring
                self._start_health_monitoring()

                # Get username safely
                username = "Unknown"
                if self.connection_config:
                    username = self.connection_config.get('username', 'Unknown')
                
                success_msg = (
                    f"✅ **Connected Successfully!**\n\n"
                    f"🌐 **Gateway**: Chicago\n"
                    f"👤 **User**: {username}\n"
                    f"⏱️ **Connection Time**: {connection_time:.2f}s\n"
                    f"🔄 **Attempt**: {self.connection_attempts}"
                )

                self._report_progress(success_msg, "success")
                return True, success_msg

            except Exception as e:
                error_msg = f"❌ **Unexpected Error**: {str(e)}"
                logger.error(f"Connection error: {traceback.format_exc()}")
                self.connection_errors.append(
                    {
                        "timestamp": datetime.now(),
                        "error": error_msg,
                        "type": "unexpected",
                        "traceback": traceback.format_exc(),
                    }
                )
                return False, error_msg

    async def disconnect(self, timeout: float = 5.0) -> None:
        """
        Disconnect from Rithmic API with proper cleanup.

        Args:
            timeout: Maximum time to wait for disconnection
        """
        async with self._lock:
            if not self.is_connected or not self.client:
                self._report_progress("ℹ️ Already disconnected")
                return

            try:
                self._report_progress("🔄 **Disconnecting from Rithmic API...**")

                # Stop health monitoring
                if self.health_check_task and not self.health_check_task.done():
                    self.health_check_task.cancel()
                    try:
                        await asyncio.wait_for(self.health_check_task, timeout=2.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass

                # Disconnect client
                if self.client:
                    try:
                        await asyncio.wait_for(
                            self.client.disconnect(), timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Disconnect timeout after {timeout}s")
                    except Exception as e:
                        logger.warning(f"Disconnect error: {e}")

                # Reset state
                self.client = None
                self.is_connected = False
                self.last_heartbeat = None

                self._report_progress("✅ **Disconnected successfully**", "success")

            except Exception as e:
                logger.error(f"Disconnect error: {e}")
                # Force reset state even if disconnect failed
                self.client = None
                self.is_connected = False
                self.last_heartbeat = None
                self._report_progress(f"⚠️ **Forced disconnect due to error**: {str(e)}")

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test the current connection health.

        Returns:
            Tuple of (is_healthy: bool, status_message: str)
        """
        if not self.is_connected or not self.client:
            return False, "❌ **Not Connected**"

        try:
            # Check client connection status
            if not self.client.is_connected():
                return False, "❌ **Client reports disconnected**"

            # Check heartbeat age
            if self.last_heartbeat:
                heartbeat_age = (datetime.now() - self.last_heartbeat).total_seconds()
                if heartbeat_age > 60:  # 1 minute threshold
                    return (
                        False,
                        f"⚠️ **Stale connection**: Last heartbeat {heartbeat_age:.0f}s ago",
                    )

            # Check connection age
            if self.connection_start_time:
                connection_age = (
                    datetime.now() - self.connection_start_time
                ).total_seconds()
                if connection_age > self.max_connection_age:
                    return (
                        False,
                        f"⚠️ **Connection aged**: {connection_age/3600:.1f}h old",
                    )

            # All checks passed
            uptime = (
                (datetime.now() - self.connection_start_time).total_seconds()
                if self.connection_start_time
                else 0
            )
            return True, f"✅ **Connection Healthy** (uptime: {uptime/60:.1f}m)"

        except Exception as e:
            return False, f"❌ **Health check failed**: {str(e)}"

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status information.

        Returns:
            Dictionary with connection status details
        """
        status = {
            "is_connected": self.is_connected,
            "connection_attempts": self.connection_attempts,
            "last_attempt": (
                self.last_connection_attempt.isoformat()
                if self.last_connection_attempt
                else None
            ),
            "connection_start": (
                self.connection_start_time.isoformat()
                if self.connection_start_time
                else None
            ),
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "uptime_seconds": None,
            "client_connected": False,
            "recent_errors": (
                self.connection_errors[-5:] if self.connection_errors else []
            ),
            "config_loaded": self.connection_config is not None,
        }

        if self.connection_start_time:
            status["uptime_seconds"] = (
                datetime.now() - self.connection_start_time
            ).total_seconds()

        if self.client:
            try:
                status["client_connected"] = self.client.is_connected()
            except Exception:
                status["client_connected"] = False

        return status

    async def get_connection_info(self) -> Dict[str, Any]:
        """
        Get detailed connection information for system status reporting.

        Returns:
            Dictionary with connection information including server details
        """
        info = self.get_connection_status()

        # Add additional connection details if available
        if self.client and self.is_connected:
            try:
                # Add server information if available
                config = self.connection_config or {}
                info["server"] = {
                    "name": config.get("server_name", "Unknown"),
                    "environment": config.get("environment", "Unknown"),
                    "version": getattr(self.client, "server_version", "Unknown"),
                }

                # Add user information if available
                info["user"] = {
                    "username": config.get("username", "Unknown"),
                    "account": config.get("account", "Unknown"),
                }
            except Exception as e:
                logger.error(f"Error getting detailed connection info: {e}")
                info["error"] = str(e)

        return info

    async def reconnect_if_needed(self) -> bool:
        """
        Check connection health and reconnect if necessary.

        Returns:
            True if connection is healthy or successfully reconnected
        """
        is_healthy, status_msg = await self.test_connection()

        if is_healthy:
            return True

        self._report_progress(f"🔄 **Reconnection needed**: {status_msg}")

        # Attempt reconnection
        try:
            await self.disconnect(timeout=3.0)
            success, message = await self.connect()

            if success:
                self._report_progress("✅ **Reconnected successfully**", "success")
                return True
            else:
                self._report_progress(f"❌ **Reconnection failed**: {message}")
                return False

        except Exception as e:
            self._report_progress(f"❌ **Reconnection error**: {str(e)}")
            return False

    def _start_health_monitoring(self):
        """Start background health monitoring task."""
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()

        self.health_check_task = asyncio.create_task(self._health_monitor_loop())

    async def _health_monitor_loop(self):
        """Background task for monitoring connection health."""
        try:
            while self.is_connected:
                await asyncio.sleep(self.heartbeat_interval)

                if not self.is_connected:
                    break

                # Update heartbeat
                self.last_heartbeat = datetime.now()

                # Check connection health
                is_healthy, _ = await self.test_connection()
                if not is_healthy:
                    logger.warning("Health check failed, attempting reconnection")
                    await self.reconnect_if_needed()

        except asyncio.CancelledError:
            logger.info("Health monitoring cancelled")
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        success, message = await self.connect()
        if not success:
            raise ConnectionError(f"Failed to connect: {message}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Singleton instance for shared connection management
_connection_manager_instance: Optional[RithmicConnectionManager] = None


def get_connection_manager(
    progress_callback: Optional[Callable] = None,
) -> RithmicConnectionManager:
    """
    Get or create the singleton connection manager instance.

    Args:
        progress_callback: Optional progress callback for new instances

    Returns:
        RithmicConnectionManager instance
    """
    global _connection_manager_instance

    if _connection_manager_instance is None:
        _connection_manager_instance = RithmicConnectionManager(progress_callback)
    elif progress_callback and not _connection_manager_instance.progress_callback:
        _connection_manager_instance.progress_callback = progress_callback

    return _connection_manager_instance


async def ensure_connection(
    progress_callback: Optional[Callable] = None,
) -> Tuple[bool, str, RithmicConnectionManager]:
    """
    Ensure a healthy connection exists, creating or reconnecting as needed.

    Args:
        progress_callback: Optional progress callback

    Returns:
        Tuple of (success: bool, message: str, connection_manager: RithmicConnectionManager)
    """
    manager = get_connection_manager(progress_callback)

    # Check if reconnection is needed
    if not await manager.reconnect_if_needed():
        # Try a fresh connection
        success, message = await manager.connect()
        return success, message, manager

    return True, "✅ **Connection ready**", manager
