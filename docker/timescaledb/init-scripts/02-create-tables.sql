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
