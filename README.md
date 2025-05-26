# NQ/ES Futures Trading System

A 3-layer machine learning system for futures trading with real-time prediction and visualization.

## System Architecture

- **Layer 1**: Development environment for data collection, model training, and backtesting
- **Layer 2**: Real-time data processing and prediction service (Docker)
- **Layer 3**: Web-based visualization dashboard (Docker)

## Quick Start

1. Set up TimescaleDB: `docker-compose up timescaledb`
2. Configure Rithmic API credentials in `.env`
3. Run Layer 1 development: `cd layer1_development && python main.py`
4. Deploy Layer 2: `cd layer2_realtime && docker build -t trading-realtime .`
5. Deploy Layer 3: `cd layer3_visualization && docker build -t trading-dashboard .`

## Historical Data Access

This system uses the async_rithmic library (version 1.4.1) to access historical market data from Rithmic. The following methods are available:

### Direct Historical Data Access

The RithmicClient class provides direct methods for accessing historical data:

```python
# Get historical time bars
bars = await client.get_historical_time_bars(
    symbol,           # e.g., "ESM5"
    exchange,         # e.g., "CME"
    start_time,       # datetime object
    end_time,         # datetime object
    TimeBarType.MINUTE_BAR,  # or TimeBarType.SECOND_BAR
    1                 # interval (e.g., 1 for 1-minute bars)
)

# Get historical tick data
ticks = await client.get_historical_tick_data(
    symbol,           # e.g., "ESM5"
    exchange,         # e.g., "CME"
    start_time,       # datetime object
    end_time          # datetime object
)
```

### Type Hints for Pylance

This project includes type stubs for the async_rithmic library to help Pylance recognize the available methods. The stubs are located in the `stubs/async_rithmic` directory.

If you encounter Pylance errors related to missing attributes or methods, you can:

1. Add the `# type: ignore` comment to the line with the error
2. Update the type stubs in the `stubs/async_rithmic` directory

### DataType Enum

The DataType enum in async_rithmic version 1.4.1 only includes the following values:

- `DataType.LAST_TRADE`
- `DataType.BBO`

There is no `DataType.HISTORY` value in this version. Historical data is accessed directly through the methods mentioned above.

## Requirements

- Python 3.9+
- Docker & Docker Compose
- Rithmic API access
- TimescaleDB

## License

Private Project
