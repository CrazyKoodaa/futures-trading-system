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

## Requirements

- Python 3.9+
- Docker & Docker Compose
- Rithmic API access
- TimescaleDB

## License

Private Project
