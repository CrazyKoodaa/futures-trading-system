from typing import List, Dict, Any, Optional, Union, Callable, Awaitable
from datetime import datetime
from enum import Enum, auto

class Gateway(Enum):
    TEST = auto()
    CHICAGO = auto()

class TimeBarType(Enum):
    SECOND_BAR = auto()
    MINUTE_BAR = auto()
    DAILY_BAR = auto()
    WEEKLY_BAR = auto()

class DataType(Enum):
    LAST_TRADE = auto()
    BBO = auto()

class InstrumentType(Enum):
    FUTURE = auto()
    OPTION = auto()
    SPREAD = auto()

class ReconnectionSettings:
    def __init__(
        self,
        max_attempts: int = 3,
        retry_delay: float = 5.0,
        backoff_factor: float = 1.5
    ) -> None: ...

class RetrySettings:
    def __init__(
        self,
        max_attempts: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 1.5
    ) -> None: ...

class RithmicClient:
    def __init__(
        self, 
        user: str, 
        password: str, 
        system_name: str, 
        app_name: str, 
        app_version: str, 
        gateway: Gateway = Gateway.TEST
    ) -> None: ...
    
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    
    # Historical data methods
    async def get_historical_time_bars(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        bar_type: TimeBarType,
        bar_interval: int
    ) -> List[Dict[str, Any]]: ...
    
    async def get_historical_tick_data(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]: ...
    
    # Market data methods
    async def get_front_month_contract(self, symbol: str, exchange: str) -> str: ...
    async def search_symbols(self, search_text: str, instrument_type: Optional[InstrumentType] = None, exchange: Optional[str] = None) -> List[Dict[str, Any]]: ...
    async def list_exchanges(self) -> List[Dict[str, Any]]: ...
    
    # Event handlers
    on_historical_time_bar: Any
    on_historical_tick: Any
    on_tick: Any
    on_time_bar: Any
    on_connected: Any
    on_disconnected: Any