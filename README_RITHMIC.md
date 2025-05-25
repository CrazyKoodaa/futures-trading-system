# Rithmic Data Collection

This directory contains scripts for collecting live and historical data from Rithmic using the `async_rithmic` library.

## Setup

1. Make sure you have the required dependencies installed:
   ```
   pip install async_rithmic pandas
   ```

2. Configure your Rithmic credentials in `config/chicago_gateway_config.py`

## Available Scripts

### 1. Collect Live Data

The `collect_live_data.py` script connects to Rithmic and collects live market data.

```bash
python collect_live_data.py
```

This script offers three options:
- Collect live market data (tick data and time bars)
- Fetch historical data
- Both live and historical data

The script automatically:
- Retrieves front month contracts for the specified symbols
- Subscribes to tick data (trades, bids, asks)
- Subscribes to 1-minute time bars
- Handles reconnection if the connection is lost
- Provides detailed logging

### 2. Collect Historical Data

The `collect_historical_data.py` script fetches historical data from Rithmic and saves it to CSV files.

```bash
python collect_historical_data.py
```

This script:
- Prompts for symbols and time range
- Retrieves front month contracts
- Fetches historical data at multiple timeframes:
  - Daily bars
  - Hourly bars
  - 15-minute bars
  - 5-minute bars
  - 1-minute bars
  - Tick data (limited to the last day to avoid excessive data)
- Saves data to CSV files in the `data/historical/{symbol}/` directory
- Creates metadata files with information about each dataset

### 3. Search Symbols

The `search_symbols.py` script provides utilities for searching symbols and retrieving contract information.

```bash
python search_symbols.py
```

This script offers a menu with options to:
- List available exchanges
- Search for symbols by name, exchange, and instrument type
- Get front month contracts for specified symbols

## Error Handling

All scripts include comprehensive error handling:
- Connection errors are automatically retried with exponential backoff
- Timeouts for requests are configurable
- Detailed logging helps diagnose issues
- Graceful shutdown on keyboard interrupt

## Data Directory Structure

Historical data is saved in the following structure:
```
data/
  historical/
    ES/
      ES_daily_bars_20250501_to_20250531.csv
      ES_daily_bars_20250501_to_20250531_metadata.json
      ES_hourly_bars_20250501_to_20250531.csv
      ...
    NQ/
      NQ_daily_bars_20250501_to_20250531.csv
      ...
```

Each data file has a corresponding metadata JSON file with information about the dataset.

## Customization

You can customize the behavior of these scripts by modifying:
- `config/chicago_gateway_config.py` - Rithmic connection settings
- The symbol lists in each script
- Time ranges for historical data
- Logging levels for more or less verbose output