# PowerShell Script to Create Futures Trading System Project Structure
# Run this script in the directory where you want to create the project structure

param(
    [string]$CreateSubfolder = "false"
)

# Use current directory instead of creating subfolder
if ($CreateSubfolder -eq "true") {
    $ProjectName = "futures-trading-system"
    $ProjectPath = Join-Path (Get-Location).Path $ProjectName
    Write-Host "Creating Futures Trading System project structure in subfolder..." -ForegroundColor Green
    Write-Host "Project will be created at: $ProjectPath" -ForegroundColor Yellow
} else {
    $ProjectPath = (Get-Location).Path
    Write-Host "Creating Futures Trading System project structure in current directory..." -ForegroundColor Green
    Write-Host "Project will be created at: $ProjectPath" -ForegroundColor Yellow
}

# Function to create directory if it doesn't exist
function New-DirectoryIfNotExists {
    param([string]$Path)
    if (!(Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "Created directory: $Path" -ForegroundColor Cyan
    }
}

# Function to create file if it doesn't exist
function New-FileIfNotExists {
    param(
        [string]$Path,
        [string]$Content = ""
    )
    if (!(Test-Path $Path)) {
        New-Item -ItemType File -Path $Path -Force | Out-Null
        if ($Content) {
            Set-Content -Path $Path -Value $Content -Encoding UTF8
        }
        Write-Host "Created file: $Path" -ForegroundColor Gray
    }
}

# Create main project directory (only if creating subfolder)
if ($CreateSubfolder -eq "true") {
    New-DirectoryIfNotExists $ProjectPath
}

# Create all directories
$directories = @(
    # Root level directories
    "config",
    "shared",
    "shared/database",
    "shared/data_models",
    "shared/utils",
    "shared/rithmic",
    
    # Layer 1 - Development
    "layer1_development",
    "layer1_development/data_collection",
    "layer1_development/data_processing",
    "layer1_development/models",
    "layer1_development/training",
    "layer1_development/evaluation",
    "layer1_development/experiments",
    "layer1_development/experiments/experiment_1_baseline",
    "layer1_development/experiments/experiment_2_features",
    "layer1_development/notebooks",
    
    # Layer 2 - Real-time
    "layer2_realtime",
    "layer2_realtime/data_stream",
    "layer2_realtime/prediction",
    "layer2_realtime/api",
    "layer2_realtime/monitoring",
    
    # Layer 3 - Visualization
    "layer3_visualization",
    "layer3_visualization/dashboard",
    "layer3_visualization/dashboard/components",
    "layer3_visualization/dashboard/callbacks",
    "layer3_visualization/data_access",
    "layer3_visualization/static",
    "layer3_visualization/static/css",
    "layer3_visualization/static/js",
    "layer3_visualization/static/images",
    
    # Data directories
    "data",
    "data/raw",
    "data/raw/NQ",
    "data/raw/ES",
    "data/processed",
    "data/processed/features",
    "data/processed/labels",
    "data/models",
    "data/models/trained",
    "data/models/checkpoints",
    "data/models/metadata",
    "data/logs",
    "data/logs/training",
    "data/logs/prediction",
    "data/logs/system",
    
    # Scripts
    "scripts",
    
    # Docker
    "docker",
    "docker/layer2",
    "docker/layer3",
    "docker/timescaledb",
    "docker/timescaledb/init-scripts",
    "docker/nginx",
    
    # Tests
    "tests",
    "tests/unit",
    "tests/unit/test_data_processing",
    "tests/unit/test_models",
    "tests/unit/test_utils",
    "tests/integration",
    "tests/integration/test_database",
    "tests/integration/test_api",
    "tests/integration/test_pipeline",
    "tests/end_to_end",
    
    # Documentation
    "docs",
    
    # Monitoring
    "monitoring",
    "monitoring/prometheus",
    "monitoring/grafana",
    "monitoring/grafana/dashboards",
    "monitoring/grafana/provisioning",
    "monitoring/logs"
)

foreach ($dir in $directories) {
    $fullPath = Join-Path $ProjectPath $dir
    New-DirectoryIfNotExists $fullPath
}

# Create root files
$rootFiles = @{
    "README.md" = @"
# NQ/ES Futures Trading System

A 3-layer machine learning system for futures trading with real-time prediction and visualization.

## System Architecture

- **Layer 1**: Development environment for data collection, model training, and backtesting
- **Layer 2**: Real-time data processing and prediction service (Docker)
- **Layer 3**: Web-based visualization dashboard (Docker)

## Quick Start

1. Set up TimescaleDB: ``docker-compose up timescaledb``
2. Configure Rithmic API credentials in ``.env``
3. Run Layer 1 development: ``cd layer1_development && python main.py``
4. Deploy Layer 2: ``cd layer2_realtime && docker build -t trading-realtime .``
5. Deploy Layer 3: ``cd layer3_visualization && docker build -t trading-dashboard .``

## Requirements

- Python 3.9+
- Docker & Docker Compose
- Rithmic API access
- TimescaleDB

## License

Private Project
"@

    ".gitignore" = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Jupyter Notebooks
.ipynb_checkpoints

# Environment variables
.env
.env.local
.env.production

# Data files
data/raw/*
!data/raw/.gitkeep
data/processed/*
!data/processed/.gitkeep
data/models/trained/*
!data/models/trained/.gitkeep

# Logs
*.log
data/logs/*
!data/logs/.gitkeep

# Docker
.docker/

# OS
.DS_Store
Thumbs.db

# Temporary files
tmp/
temp/
"@

    ".env.template" = @"
# Rithmic API Configuration
RITHMIC_USER=your_username
RITHMIC_PASSWORD=your_password
RITHMIC_SYSTEM_NAME=your_system_name
RITHMIC_EXCHANGE=CME

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=secure_password

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=True

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Dashboard Configuration
DASH_HOST=0.0.0.0
DASH_PORT=8050
"@

    "requirements.txt" = @"
# Core dependencies (Python 3.11 compatible)
typing-extensions>=4.8.0
numpy>=1.21.0,<1.27.0
pandas>=1.5.0,<2.3.0
scipy>=1.9.0
scikit-learn>=1.1.0,<1.4.0
joblib>=1.3.0

# Database
psycopg2-binary>=2.9.7
sqlalchemy>=2.0.0,<2.1.0

# Async processing
aiohttp>=3.8.5
asyncpg>=0.28.0
anyio>=4.0.0

# Machine Learning 
xgboost>=1.6.0
lightgbm>=3.3.0
torch>=2.0.0
tensorflow>=2.12.0,<2.20.0

# Data processing
pandas-ta==0.3.14b0
yfinance>=0.2.18
beautifulsoup4>=4.12.0

# Visualization
plotly>=5.15.0
dash>=3.0.0
dash-bootstrap-components>=1.4.0

# API
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
pydantic-core>=2.0.0

# Monitoring
prometheus-client>=0.17.0

# Configuration
pyyaml>=6.0.1
python-dotenv>=1.0.0

# Logging
loguru>=0.7.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Additional utilities
requests>=2.31.0
"@

    "setup.py" = @"
from setuptools import setup, find_packages

setup(
    name="futures-trading-system",
    version="0.1.0",
    description="NQ/ES Futures Trading System with ML Predictions",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0,<1.27.0",
        "pandas>=1.5.0,<2.3.0",
        "scikit-learn>=1.1.0,<1.4.0",
        "psycopg2-binary>=2.9.7",
        "sqlalchemy>=1.4.0,<2.1.0",
        "fastapi>=0.100.0",
        "plotly>=5.15.0",
        "dash>=2.14.0",
        "xgboost>=1.6.0",
        "lightgbm>=3.3.0",
    ],
    python_requires=">=3.11,<3.13",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3.11",
    ],
)
"@

    "docker-compose.yml" = @"
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    container_name: trading_timescaledb
    environment:
      POSTGRES_DB: trading_db
      POSTGRES_USER: trading_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./docker/timescaledb/init-scripts:/docker-entrypoint-initdb.d
    networks:
      - trading_network

  realtime_processor:
    build:
      context: ./layer2_realtime
      dockerfile: Dockerfile
    container_name: trading_realtime
    environment:
      - POSTGRES_HOST=timescaledb
      - POSTGRES_PORT=5432
      - POSTGRES_DB=trading_db
      - POSTGRES_USER=trading_user
      - POSTGRES_PASSWORD=secure_password
    ports:
      - "8000:8000"
    depends_on:
      - timescaledb
    networks:
      - trading_network
    volumes:
      - ./data/models:/app/models
      - ./data/logs:/app/logs

  dashboard:
    build:
      context: ./layer3_visualization
      dockerfile: Dockerfile
    container_name: trading_dashboard
    environment:
      - POSTGRES_HOST=timescaledb
      - POSTGRES_PORT=5432
      - POSTGRES_DB=trading_db
      - POSTGRES_USER=trading_user
      - POSTGRES_PASSWORD=secure_password
    ports:
      - "8050:8050"
    depends_on:
      - timescaledb
      - realtime_processor
    networks:
      - trading_network

  prometheus:
    image: prom/prometheus:latest
    container_name: trading_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - trading_network

  grafana:
    image: grafana/grafana:latest
    container_name: trading_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    networks:
      - trading_network

volumes:
  timescale_data:
  grafana_data:

networks:
  trading_network:
    driver: bridge
"@

    "Makefile" = @"
.PHONY: help setup install test lint clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  setup       - Set up development environment"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  clean       - Clean temporary files"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up   - Start Docker services"
	@echo "  docker-down - Stop Docker services"

setup:
	python -m venv venv
	./venv/Scripts/activate && pip install -r requirements.txt
	cp .env.template .env

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=.

lint:
	flake8 --max-line-length=100 .
	black --check .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
"@
}

foreach ($file in $rootFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $rootFiles[$file]
}

# Create config files
$configFiles = @{
    "config/__init__.py" = ""
    "config/development.yaml" = @"
database:
  host: localhost
  port: 5432
  name: trading_db
  user: trading_user
  password: secure_password

rithmic:
  system_name: your_system_name
  user: your_username
  password: your_password
  exchange: CME

trading:
  instruments:
    - NQ
    - ES
  timeframes:
    - 1s
    - 5s
    - 1m
    - 5m

models:
  direction_prediction:
    lookback_minutes: 60
    prediction_horizon: 10
  pip_movement:
    target_pips: 40
    timeframe_minutes: 5

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"@
    "config/production.yaml" = @"
database:
  host: timescaledb
  port: 5432
  name: trading_db
  user: trading_user
  password: secure_password

rithmic:
  system_name: your_system_name
  user: your_username
  password: your_password
  exchange: CME

trading:
  instruments:
    - NQ
    - ES
  timeframes:
    - 1s
    - 5s
    - 1m
    - 5m

models:
  direction_prediction:
    lookback_minutes: 60
    prediction_horizon: 10
  pip_movement:
    target_pips: 40
    timeframe_minutes: 5

logging:
  level: WARNING
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"@
    "config/database.yaml" = @"
timescaledb:
  hypertables:
    market_data:
      time_column: timestamp
      chunk_time_interval: 1h
    predictions:
      time_column: timestamp
      chunk_time_interval: 1d
    trades:
      time_column: timestamp
      chunk_time_interval: 1d

indexes:
  - table: market_data
    columns: [symbol, timestamp]
  - table: predictions
    columns: [symbol, timestamp, model_version]
"@
    "config/rithmic_config.yaml" = @"
connection:
  timeout: 30
  retry_attempts: 3
  heartbeat_interval: 30

instruments:
  NQ:
    full_name: "E-mini NASDAQ 100"
    tick_size: 0.25
    point_value: 20
    margin_requirement: 14000
  ES:
    full_name: "E-mini S&P 500"
    tick_size: 0.25
    point_value: 50
    margin_requirement: 12000

data_types:
  - tick
  - quote
  - trade
  - time_and_sales
"@
}

foreach ($file in $configFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $configFiles[$file]
}

# Create shared module files
$sharedFiles = @{
    "shared/__init__.py" = ""
    "shared/database/__init__.py" = ""
    "shared/database/connection.py" = "# Database connection management"
    "shared/database/models.py" = "# SQLAlchemy models for TimescaleDB"
    "shared/database/timescale_manager.py" = "# TimescaleDB specific operations"
    "shared/data_models/__init__.py" = ""
    "shared/data_models/market_data.py" = "# Market data structures"
    "shared/data_models/predictions.py" = "# Prediction data structures"
    "shared/data_models/trades.py" = "# Trade data structures"
    "shared/utils/__init__.py" = ""
    "shared/utils/logging_config.py" = "# Logging configuration"
    "shared/utils/constants.py" = "# System constants"
    "shared/utils/helpers.py" = "# Utility functions"
    "shared/rithmic/__init__.py" = ""
    "shared/rithmic/client.py" = "# Rithmic API client"
    "shared/rithmic/data_parser.py" = "# Rithmic data parsing utilities"
}

foreach ($file in $sharedFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $sharedFiles[$file]
}

# Create Layer 1 files
$layer1Files = @{
    "layer1_development/__init__.py" = ""
    "layer1_development/README.md" = @"
# Layer 1: Development Environment

Windows 11 development environment for:
- Historical data collection from Rithmic
- Feature engineering and data preprocessing
- Model training and validation
- Backtesting and performance analysis

## Usage

1. Configure Rithmic credentials in config.yaml
2. Run historical data collection: ``python -m data_collection.historical_collector``
3. Train models: ``python -m training.trainer``
4. Evaluate performance: ``python -m evaluation.backtester``
"@
    "layer1_development/requirements.txt" = @"
# Additional Layer 1 specific dependencies
jupyterlab>=3.4.0
matplotlib>=3.5.0
seaborn>=0.11.0
yfinance>=0.1.70
ipykernel>=6.15.0
black>=22.0.0
flake8>=5.0.0
"@
    "layer1_development/main.py" = "# Main entry point for Layer 1 development"
    "layer1_development/config.yaml" = @"
# Layer 1 specific configuration
data_collection:
  start_date: "2023-01-01"
  end_date: "2024-12-31"
  instruments: ["NQ", "ES"]
  
model_training:
  train_split: 0.8
  validation_split: 0.1
  test_split: 0.1
  
backtesting:
  initial_capital: 100000
  commission_per_trade: 2.50
"@
    "layer1_development/data_collection/__init__.py" = ""
    "layer1_development/data_collection/historical_collector.py" = "# Historical data collection from Rithmic"
    "layer1_development/data_collection/async_data_fetcher.py" = "# Async data fetching utilities"
    "layer1_development/data_processing/__init__.py" = ""
    "layer1_development/data_processing/preprocessor.py" = "# Data preprocessing pipeline"
    "layer1_development/data_processing/feature_engineering.py" = "# Feature engineering for ML models"
    "layer1_development/data_processing/data_validator.py" = "# Data quality validation"
    "layer1_development/models/__init__.py" = ""
    "layer1_development/models/base_model.py" = "# Base model class"
    "layer1_development/models/direction_predictor.py" = "# 10-minute direction prediction model"
    "layer1_development/models/pip_movement_predictor.py" = "# 40-pip movement prediction model"
    "layer1_development/models/ensemble_model.py" = "# Ensemble model combining predictions"
    "layer1_development/training/__init__.py" = ""
    "layer1_development/training/trainer.py" = "# Model training pipeline"
    "layer1_development/training/hyperparameter_tuning.py" = "# Hyperparameter optimization"
    "layer1_development/training/cross_validation.py" = "# Cross-validation utilities"
    "layer1_development/evaluation/__init__.py" = ""
    "layer1_development/evaluation/backtester.py" = "# Backtesting engine"
    "layer1_development/evaluation/metrics.py" = "# Performance metrics calculation"
    "layer1_development/evaluation/performance_analyzer.py" = "# Performance analysis tools"
    "layer1_development/experiments/__init__.py" = ""
    "layer1_development/experiments/experiment_tracking.py" = "# Experiment tracking utilities"
    "layer1_development/notebooks/data_exploration.ipynb" = ""
    "layer1_development/notebooks/feature_analysis.ipynb" = ""
    "layer1_development/notebooks/model_comparison.ipynb" = ""
}

foreach ($file in $layer1Files.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $layer1Files[$file]
}

# Create Layer 2 files
$layer2Files = @{
    "layer2_realtime/Dockerfile" = @"
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
"@
    "layer2_realtime/requirements.txt" = @"
fastapi>=0.85.0
uvicorn>=0.18.0
asyncio
aiohttp>=3.8.0
psycopg2-binary>=2.9.0
sqlalchemy>=1.4.0
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=1.0.0
torch>=1.12.0
pydantic>=1.10.0
python-dotenv>=0.20.0
loguru>=0.6.0
"@
    "layer2_realtime/main.py" = "# Main entry point for real-time processing service"
    "layer2_realtime/config.yaml" = @"
# Layer 2 real-time processing configuration
api:
  host: 0.0.0.0
  port: 8000
  
realtime:
  update_interval: 1  # seconds
  batch_size: 100
  max_queue_size: 1000

prediction:
  confidence_threshold: 0.6
  model_update_interval: 3600  # seconds
"@
    "layer2_realtime/data_stream/__init__.py" = ""
    "layer2_realtime/data_stream/realtime_collector.py" = "# Real-time data collection from Rithmic"
    "layer2_realtime/data_stream/stream_processor.py" = "# Stream processing pipeline"
    "layer2_realtime/prediction/__init__.py" = ""
    "layer2_realtime/prediction/model_loader.py" = "# Model loading and management"
    "layer2_realtime/prediction/realtime_predictor.py" = "# Real-time prediction service"
    "layer2_realtime/prediction/confidence_calculator.py" = "# Confidence score calculation"
    "layer2_realtime/api/__init__.py" = ""
    "layer2_realtime/api/prediction_api.py" = "# FastAPI prediction endpoints"
    "layer2_realtime/api/health_check.py" = "# Health check endpoints"
    "layer2_realtime/monitoring/__init__.py" = ""
    "layer2_realtime/monitoring/performance_monitor.py" = "# Performance monitoring"
    "layer2_realtime/monitoring/alert_system.py" = "# Alert system for anomalies"
}

foreach ($file in $layer2Files.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $layer2Files[$file]
}

# Create Layer 3 files
$layer3Files = @{
    "layer3_visualization/Dockerfile" = @"
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050

CMD ["python", "main.py"]
"@
    "layer3_visualization/requirements.txt" = @"
dash>=2.6.0
dash-bootstrap-components>=1.2.0
plotly>=5.0.0
pandas>=1.3.0
psycopg2-binary>=2.9.0
sqlalchemy>=1.4.0
requests>=2.28.0
python-dotenv>=0.20.0
loguru>=0.6.0
"@
    "layer3_visualization/main.py" = "# Main entry point for visualization dashboard"
    "layer3_visualization/config.yaml" = @"
# Layer 3 visualization configuration
dashboard:
  host: 0.0.0.0
  port: 8050
  debug: false
  
chart_settings:
  update_interval: 5000  # milliseconds
  max_data_points: 10000
  default_timeframe: "1h"

colors:
  bullish: "#00ff00"
  bearish: "#ff0000"
  neutral: "#ffff00"
"@
    "layer3_visualization/dashboard/__init__.py" = ""
    "layer3_visualization/dashboard/app.py" = "# Main Plotly Dash application"
    "layer3_visualization/dashboard/components/__init__.py" = ""
    "layer3_visualization/dashboard/components/price_chart.py" = "# Price chart component"
    "layer3_visualization/dashboard/components/confidence_chart.py" = "# Confidence chart component"
    "layer3_visualization/dashboard/components/trade_signals.py" = "# Trade signals component"
    "layer3_visualization/dashboard/components/performance_metrics.py" = "# Performance metrics component"
    "layer3_visualization/dashboard/callbacks/__init__.py" = ""
    "layer3_visualization/dashboard/callbacks/chart_callbacks.py" = "# Chart update callbacks"
    "layer3_visualization/dashboard/callbacks/trade_callbacks.py" = "# Trade-related callbacks"
    "layer3_visualization/data_access/__init__.py" = ""
    "layer3_visualization/data_access/historical_data.py" = "# Historical data access"
    "layer3_visualization/data_access/realtime_data.py" = "# Real-time data access"
    "layer3_visualization/static/css/style.css" = "/* Custom CSS styles */"
    "layer3_visualization/static/js/custom.js" = "// Custom JavaScript"
}

foreach ($file in $layer3Files.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $layer3Files[$file]
}

# Create script files
$scriptFiles = @{
    "scripts/setup_database.py" = "# Database setup and initialization script"
    "scripts/download_historical_data.py" = "# Historical data download script"
    "scripts/train_models.py" = "# Model training automation script"
    "scripts/deploy_containers.py" = "# Container deployment script"
    "scripts/backup_data.py" = "# Data backup script"
}

foreach ($file in $scriptFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $scriptFiles[$file]
}

# Create Docker files
$dockerFiles = @{
    "docker/layer2/Dockerfile" = @"
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY layer2_realtime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY layer2_realtime/ .

EXPOSE 8000

CMD ["uvicorn", "api.prediction_api:app", "--host", "0.0.0.0", "--port", "8000"]
"@
    "docker/layer2/docker-compose.layer2.yml" = @"
version: '3.8'

services:
  realtime_processor:
    build:
      context: ../../
      dockerfile: docker/layer2/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=timescaledb
      - POSTGRES_PORT=5432
    volumes:
      - ../../data/models:/app/models
      - ../../data/logs:/app/logs
"@
    "docker/layer3/Dockerfile" = @"
FROM python:3.9-slim

WORKDIR /app

COPY layer3_visualization/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY layer3_visualization/ .

EXPOSE 8050

CMD ["python", "main.py"]
"@
    "docker/layer3/docker-compose.layer3.yml" = @"
version: '3.8'

services:
  dashboard:
    build:
      context: ../../
      dockerfile: docker/layer3/Dockerfile
    ports:
      - "8050:8050"
    environment:
      - POSTGRES_HOST=timescaledb
      - POSTGRES_PORT=5432
"@
    "docker/timescaledb/Dockerfile" = @"
FROM timescale/timescaledb:latest-pg14

COPY init-scripts/ /docker-entrypoint-initdb.d/
"@
    "docker/timescaledb/init-scripts/01-create-extensions.sql" = @"
-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create additional extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_cron;
"@
    "docker/timescaledb/init-scripts/02-create-tables.sql" = @"
-- Create market data table
CREATE TABLE market_data (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    volume INTEGER,
    bid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    PRIMARY KEY (timestamp, symbol)
);

-- Create hypertable
SELECT create_hypertable('market_data', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- Create predictions table
CREATE TABLE predictions (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    direction_prediction INTEGER, -- -1, 0, 1
    confidence_score DECIMAL(5, 2), -- -100 to 100
    pip_movement_prediction DECIMAL(8, 4),
    PRIMARY KEY (timestamp, symbol, model_version)
);

-- Create hypertable for predictions
SELECT create_hypertable('predictions', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Create trades table
CREATE TABLE trades (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    confidence_at_entry DECIMAL(5, 2),
    exit_timestamp TIMESTAMPTZ,
    exit_price DECIMAL(10, 4),
    pnl DECIMAL(10, 2),
    PRIMARY KEY (timestamp, symbol)
);

-- Create hypertable for trades
SELECT create_hypertable('trades', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Create indexes
CREATE INDEX idx_market_data_symbol_timestamp ON market_data (symbol, timestamp DESC);
CREATE INDEX idx_predictions_symbol_timestamp ON predictions (symbol, timestamp DESC);
CREATE INDEX idx_trades_symbol_timestamp ON trades (symbol, timestamp DESC);
"@
    "docker/timescaledb/postgresql.conf" = @"
# TimescaleDB specific configuration
shared_preload_libraries = 'timescaledb'

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL settings
wal_level = replica
max_wal_size = 1GB
min_wal_size = 80MB

# Connection settings
max_connections = 100

# Logging
log_statement = 'all'
log_destination = 'stderr'
logging_collector = on
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
"@
    "docker/nginx/Dockerfile" = @"
FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
"@
    "docker/nginx/nginx.conf" = @"
events {
    worker_connections 1024;
}

http {
    upstream api {
        server realtime_processor:8000;
    }
    
    upstream dashboard {
        server dashboard:8050;
    }
    
    server {
        listen 80;
        
        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location / {
            proxy_pass http://dashboard/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
"@
}

foreach ($file in $dockerFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $dockerFiles[$file]
}

# Create test files
$testFiles = @{
    "tests/__init__.py" = ""
    "tests/conftest.py" = @"
import pytest
import asyncio
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        yield tmp.name
    os.unlink(tmp.name)
"@
    "tests/unit/__init__.py" = ""
    "tests/unit/test_data_processing/__init__.py" = ""
    "tests/unit/test_models/__init__.py" = ""
    "tests/unit/test_utils/__init__.py" = ""
    "tests/integration/__init__.py" = ""
    "tests/integration/test_database/__init__.py" = ""
    "tests/integration/test_api/__init__.py" = ""
    "tests/integration/test_pipeline/__init__.py" = ""
    "tests/end_to_end/__init__.py" = ""
    "tests/end_to_end/test_full_system.py" = "# End-to-end system tests"
}

foreach ($file in $testFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $testFiles[$file]
}

# Create documentation files
$docFiles = @{
    "docs/architecture.md" = "# System Architecture Documentation"
    "docs/api_documentation.md" = "# API Documentation"
    "docs/deployment_guide.md" = "# Deployment Guide"
    "docs/model_documentation.md" = "# Model Documentation"
    "docs/troubleshooting.md" = "# Troubleshooting Guide"
}

foreach ($file in $docFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $docFiles[$file]
}

# Create monitoring configuration files
$monitoringFiles = @{
    "monitoring/prometheus/prometheus.yml" = @"
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'trading-realtime'
    static_configs:
      - targets: ['realtime_processor:8000']
    
  - job_name: 'trading-dashboard'
    static_configs:
      - targets: ['dashboard:8050']
"@
    "monitoring/grafana/dashboards/trading_dashboard.json" = "{}"
    "monitoring/grafana/provisioning/datasources.yml" = @"
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
"@
    "monitoring/logs/log_config.yaml" = @"
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout
  
  file:
    class: logging.FileHandler
    level: INFO
    formatter: default
    filename: /app/logs/system.log

loggers:
  '':
    level: INFO
    handlers: [console, file]
    propagate: no
"@
}

foreach ($file in $monitoringFiles.Keys) {
    $filePath = Join-Path $ProjectPath $file
    New-FileIfNotExists $filePath $monitoringFiles[$file]
}

# Create .gitkeep files for empty directories that need to be tracked
$gitkeepDirs = @(
    "data/raw/NQ",
    "data/raw/ES", 
    "data/processed/features",
    "data/processed/labels",
    "data/models/trained",
    "data/models/checkpoints",
    "data/models/metadata",
    "data/logs/training",
    "data/logs/prediction",
    "data/logs/system",
    "layer1_development/experiments/experiment_1_baseline",
    "layer1_development/experiments/experiment_2_features"
)

foreach ($dir in $gitkeepDirs) {
    $gitkeepPath = Join-Path $ProjectPath "$dir/.gitkeep"
    New-FileIfNotExists $gitkeepPath ""
}

Write-Host ""
Write-Host "✅ Project structure created successfully!" -ForegroundColor Green
Write-Host "Project created in: $ProjectPath" -ForegroundColor Yellow

# Verify Python version in venv
$venvPython = Join-Path $ProjectPath "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    try {
        $venvVersion = & $venvPython --version 2>$null
        Write-Host "Virtual environment Python version: $venvVersion" -ForegroundColor Green
        
        if ($venvVersion -match "Python 3\.11\.") {
            Write-Host "✅ Correct Python 3.11 version in virtual environment!" -ForegroundColor Green
        } else {
            Write-Warning "⚠️  Virtual environment is not using Python 3.11!"
        }
    }
    catch {
        Write-Warning "Could not verify virtual environment Python version"
    }
} else {
    Write-Host "ℹ️  Virtual environment not created. Create manually with:" -ForegroundColor Yellow
    Write-Host "   py -3.11 -m venv venv" -ForegroundColor White
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
if ($CreateSubfolder -eq "true") {
    Write-Host "1. Navigate to project directory: cd $ProjectName" -ForegroundColor White
    Write-Host "2. Copy and configure environment: cp .env.template .env" -ForegroundColor White
    Write-Host "3. Activate virtual environment: .\venv\Scripts\activate" -ForegroundColor White
    Write-Host "4. Verify Python version: python --version (should be 3.11.x)" -ForegroundColor White
    Write-Host "5. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "6. Start TimescaleDB: docker-compose up timescaledb" -ForegroundColor White
} else {
    Write-Host "1. Copy and configure environment: copy .env.template .env" -ForegroundColor White
    Write-Host "2. Activate virtual environment: .\venv\Scripts\activate" -ForegroundColor White
    Write-Host "3. Verify Python version: python --version (should be 3.11.x)" -ForegroundColor White  
    Write-Host "4. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "5. Start TimescaleDB: docker-compose up timescaledb" -ForegroundColor White
}
Write-Host ""
if (Test-Path (Join-Path $ProjectPath "venv\Scripts\activate")) {
    Write-Host "🚀 Ready to start! Activate with: .\venv\Scripts\activate" -ForegroundColor Green
} else {
    Write-Host "⚠️  Create virtual environment first: py -3.11 -m venv venv" -ForegroundColor Yellow
}
Write-Host "Happy coding! 🚀" -ForegroundColor Green