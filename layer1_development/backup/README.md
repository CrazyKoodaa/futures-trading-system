# Layer 1: Development Environment

Windows 11 development environment for:
- Historical data collection from Rithmic
- Feature engineering and data preprocessing
- Model training and validation
- Backtesting and performance analysis

## Usage

1. Configure Rithmic credentials in config.yaml
2. Run historical data collection: `python -m data_collection.historical_collector`
3. Train models: `python -m training.trainer`
4. Evaluate performance: `python -m evaluation.backtester`
