-- TimescaleDB Schema for Futures Trading with Exchange Information
-- File: docker/timescaledb/init-scripts/03-create-futures-tables.sql

-- Create extension if not exists
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =====================================================
-- EXCHANGES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS exchanges (
    exchange_id SERIAL PRIMARY KEY,
    exchange_name VARCHAR(10) NOT NULL UNIQUE,  -- CME, CBOT, NYMEX, COMEX
    exchange_code VARCHAR(10) NOT NULL UNIQUE,  -- XCME, XCBT, XNYM, XCOM
    full_name VARCHAR(100) NOT NULL,
    country VARCHAR(3) DEFAULT 'USA',
    timezone VARCHAR(50) DEFAULT 'America/Chicago',
    website VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert major futures exchanges
INSERT INTO exchanges (exchange_name, exchange_code, full_name, timezone) VALUES
('CME', 'XCME', 'Chicago Mercantile Exchange', 'America/Chicago'),
('CBOT', 'XCBT', 'Chicago Board of Trade', 'America/Chicago'),
('NYMEX', 'XNYM', 'New York Mercantile Exchange', 'America/New_York'),
('COMEX', 'XCOM', 'Commodity Exchange', 'America/New_York'),
('ICE', 'XICE', 'Intercontinental Exchange', 'America/New_York'),
('EUREX', 'XEUR', 'Eurex Exchange', 'Europe/Frankfurt')
ON CONFLICT (exchange_name) DO NOTHING;

-- =====================================================
-- INSTRUMENTS TABLE  
-- =====================================================
CREATE TABLE IF NOT EXISTS instruments (
    instrument_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,        -- NQ, ES, YM, RTY
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    full_name VARCHAR(100) NOT NULL,
    product_code VARCHAR(10),
    tick_size DECIMAL(10,6) NOT NULL,
    point_value DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    contract_months VARCHAR(20) DEFAULT 'HMUZ',  -- Valid months
    min_price_increment DECIMAL(10,6),
    trading_hours VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert major futures instruments
INSERT INTO instruments (symbol, exchange_id, full_name, product_code, tick_size, point_value, contract_months, trading_hours) VALUES
('NQ', (SELECT exchange_id FROM exchanges WHERE exchange_name = 'CME'), 'E-mini NASDAQ 100', 'NQ', 0.25, 20.00, 'HMUZ', '23:00-22:00'),
('ES', (SELECT exchange_id FROM exchanges WHERE exchange_name = 'CME'), 'E-mini S&P 500', 'ES', 0.25, 50.00, 'HMUZ', '23:00-22:00'),
('YM', (SELECT exchange_id FROM exchanges WHERE exchange_name = 'CBOT'), 'E-mini Dow Jones', 'YM', 1.00, 5.00, 'HMUZ', '23:00-22:00'),
('RTY', (SELECT exchange_id FROM exchanges WHERE exchange_name = 'CME'), 'E-mini Russell 2000', 'RTY', 0.10, 50.00, 'HMUZ', '23:00-22:00')
ON CONFLICT (symbol) DO NOTHING;

-- =====================================================
-- CONTRACTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS contracts (
    contract_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL UNIQUE,       -- NQZ24, ESH25
    exchange_id INTEGER REFERENCES exchanges(exchange_id),
    instrument_id INTEGER REFERENCES instruments(instrument_id),
    month_letter CHAR(1) NOT NULL,              -- Z, H, M, U
    contract_year INTEGER NOT NULL,             -- 2024, 2025
    expiration_date TIMESTAMPTZ,
    first_notice_date TIMESTAMPTZ,
    last_trading_date TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    volume_today INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_contract_instrument FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    CONSTRAINT fk_contract_exchange FOREIGN KEY (exchange_id) REFERENCES exchanges(exchange_id)
);

-- Index for fast contract lookups
CREATE INDEX IF NOT EXISTS idx_contracts_symbol_contract ON contracts(symbol, contract);
CREATE INDEX IF NOT EXISTS idx_contracts_active ON contracts(is_active, expiration_date);
CREATE INDEX IF NOT EXISTS idx_contracts_exchange ON contracts(exchange_id);

-- =====================================================
-- MARKET DATA SECONDS TABLE (Main tick data)
-- =====================================================
CREATE TABLE IF NOT EXISTS market_data_seconds (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,              -- CME, CBOT, etc.
    exchange_code VARCHAR(10),                  -- XCME, XCBT, etc.
    
    -- OHLCV data
    open DECIMAL(12,4) NOT NULL,
    high DECIMAL(12,4) NOT NULL,
    low DECIMAL(12,4) NOT NULL,
    close DECIMAL(12,4) NOT NULL,
    volume INTEGER DEFAULT 0,
    tick_count INTEGER DEFAULT 0,
    
    -- Additional price info
    vwap DECIMAL(12,4),                        -- Volume Weighted Average Price
    bid DECIMAL(12,4),                         -- Best bid
    ask DECIMAL(12,4),                         -- Best ask
    spread DECIMAL(12,4),                      -- Bid-ask spread
    
    -- Market data quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,  -- 0.0 to 1.0
    is_regular_hours BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (timestamp, symbol, contract, exchange)
);

-- Create hypertable for time-series optimization (1-minute chunks)
SELECT create_hypertable('market_data_seconds', 'timestamp', 
    chunk_time_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- =====================================================
-- RAW TICK DATA TABLE (Optional - for detailed analysis)
-- =====================================================
CREATE TABLE IF NOT EXISTS raw_tick_data (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    
    -- Tick details
    price DECIMAL(12,4) NOT NULL,
    size INTEGER DEFAULT 0,
    tick_type VARCHAR(10) NOT NULL,             -- 'trade', 'bid', 'ask'
    
    -- Exchange info
    exchange_timestamp TIMESTAMPTZ,
    sequence_number BIGINT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (timestamp, symbol, contract, exchange, sequence_number)
);

-- Create hypertable for raw ticks (10-second chunks due to high volume)
SELECT create_hypertable('raw_tick_data', 'timestamp', 
    chunk_time_interval => INTERVAL '10 seconds',
    if_not_exists => TRUE
);

-- =====================================================
-- AGGREGATED MINUTES TABLE (1-minute bars)
-- =====================================================
CREATE TABLE IF NOT EXISTS market_data_minutes (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    
    -- OHLCV
    open DECIMAL(12,4) NOT NULL,
    high DECIMAL(12,4) NOT NULL,
    low DECIMAL(12,4) NOT NULL,
    close DECIMAL(12,4) NOT NULL,
    volume INTEGER DEFAULT 0,
    tick_count INTEGER DEFAULT 0,
    
    -- Additional metrics
    vwap DECIMAL(12,4),
    avg_spread DECIMAL(12,4),
    max_spread DECIMAL(12,4),
    trade_count INTEGER DEFAULT 0,
    
    PRIMARY KEY (timestamp, symbol, contract, exchange)
);

-- Create hypertable for minutes (1-hour chunks)
SELECT create_hypertable('market_data_minutes', 'timestamp', 
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- =====================================================
-- FEATURES TABLE (Technical indicators with exchange)
-- =====================================================
CREATE TABLE IF NOT EXISTS features (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,              -- 1m, 5m, 15m, 1h
    
    -- Trend indicators
    sma_5 DECIMAL(12,4),
    sma_10 DECIMAL(12,4),
    sma_20 DECIMAL(12,4),
    sma_50 DECIMAL(12,4),
    ema_12 DECIMAL(12,4),
    ema_26 DECIMAL(12,4),
    macd DECIMAL(12,6),
    macd_signal DECIMAL(12,6),
    macd_histogram DECIMAL(12,6),
    
    -- Momentum indicators
    rsi DECIMAL(5,2),
    stoch_k DECIMAL(5,2),
    stoch_d DECIMAL(5,2),
    williams_r DECIMAL(5,2),
    roc DECIMAL(8,4),
    
    -- Volatility indicators  
    bb_upper DECIMAL(12,4),
    bb_middle DECIMAL(12,4),
    bb_lower DECIMAL(12,4),
    bb_width DECIMAL(8,4),
    atr DECIMAL(8,4),
    
    -- Volume indicators
    volume_sma DECIMAL(12,2),
    volume_ratio DECIMAL(6,3),
    obv BIGINT,
    
    -- Exchange-specific features
    relative_volume DECIMAL(6,3),              -- Volume vs exchange average
    exchange_rank INTEGER,                     -- Volume rank vs other exchanges
    
    PRIMARY KEY (timestamp, symbol, contract, exchange, timeframe)
);

-- Create hypertable for features (1-day chunks)
SELECT create_hypertable('features', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- =====================================================
-- PREDICTIONS TABLE (With exchange context)
-- =====================================================
CREATE TABLE IF NOT EXISTS predictions (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    
    -- Model information
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(20) NOT NULL,           -- 'xgboost', 'lstm', 'ensemble'
    
    -- Predictions
    direction_prediction INTEGER,              -- -1, 0, 1 (short, neutral, long)
    confidence_score DECIMAL(5,2),             -- -100 to +100
    pip_movement_prediction DECIMAL(8,4),      -- Expected price movement
    
    -- Probabilities
    long_probability DECIMAL(5,4),             -- 0.0 to 1.0
    short_probability DECIMAL(5,4),            -- 0.0 to 1.0
    
    -- Time horizons
    prediction_horizon_minutes INTEGER,        -- 5, 10, 15, 30 minutes
    
    -- Exchange-specific adjustments
    exchange_adjustment_factor DECIMAL(6,4) DEFAULT 1.0,
    
    -- Metadata
    features_used TEXT[],                      -- Array of feature names used
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (timestamp, symbol, contract, exchange, model_version)
);

-- Create hypertable for predictions (1-day chunks)
SELECT create_hypertable('predictions', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- =====================================================
-- TRADES TABLE (With exchange routing info)  
-- =====================================================
CREATE TABLE IF NOT EXISTS trades (
    trade_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    contract VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    
    -- Trade details
    side VARCHAR(10) NOT NULL,                 -- 'BUY', 'SELL'
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL,
    
    -- Exit details (filled when trade closes)
    exit_timestamp TIMESTAMPTZ,
    exit_price DECIMAL(12,4),
    
    -- Performance
    pnl DECIMAL(12,2),                        -- Profit/Loss
    pnl_percent DECIMAL(8,4),                 -- P&L percentage
    commission DECIMAL(8,2) DEFAULT 0,
    
    -- Model context
    confidence_at_entry DECIMAL(5,2),
    model_version VARCHAR(50),
    
    -- Exchange routing
    route_exchange VARCHAR(10),               -- Where order was routed
    execution_venue VARCHAR(20),             -- Specific venue within exchange
    
    -- Trade metadata
    trade_type VARCHAR(20) DEFAULT 'ALGO',   -- 'ALGO', 'MANUAL', 'EMERGENCY'
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable for trades (1-day chunks)
SELECT create_hypertable('trades', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Market data seconds indexes
CREATE INDEX IF NOT EXISTS idx_market_data_seconds_symbol_time ON market_data_seconds (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_seconds_contract_time ON market_data_seconds (contract, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_seconds_exchange_time ON market_data_seconds (exchange, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_seconds_volume ON market_data_seconds (volume DESC) WHERE volume > 0;

-- Raw tick data indexes (careful with size)
CREATE INDEX IF NOT EXISTS idx_raw_tick_data_contract_time ON raw_tick_data (contract, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_raw_tick_data_type ON raw_tick_data (tick_type, timestamp DESC);

-- Features indexes
CREATE INDEX IF NOT EXISTS idx_features_symbol_timeframe_time ON features (symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_features_exchange_time ON features (exchange, timestamp DESC);

-- Predictions indexes
CREATE INDEX IF NOT EXISTS idx_predictions_symbol_model_time ON predictions (symbol, model_version, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions (confidence_score DESC) WHERE ABS(confidence_score) > 50;

-- Trades indexes
CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades (pnl DESC);
CREATE INDEX IF NOT EXISTS idx_trades_exchange ON trades (exchange, timestamp DESC);

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- Current active contracts by exchange
CREATE OR REPLACE VIEW v_active_contracts AS
SELECT 
    c.contract,
    c.symbol,
    e.exchange_name,
    e.exchange_code,
    i.full_name,
    i.tick_size,
    i.point_value,
    c.expiration_date,
    c.is_active
FROM contracts c
JOIN exchanges e ON c.exchange_id = e.exchange_id
JOIN instruments i ON c.instrument_id = i.instrument_id
WHERE c.is_active = TRUE
ORDER BY c.symbol, c.expiration_date;

-- Latest market data with exchange info
CREATE OR REPLACE VIEW v_latest_market_data AS
SELECT DISTINCT ON (symbol, contract, exchange)
    timestamp,
    symbol,
    contract,
    exchange,
    close as last_price,
    volume,
    bid,
    ask,
    spread
FROM market_data_seconds
ORDER BY symbol, contract, exchange, timestamp DESC;

-- Daily volume by exchange
CREATE OR REPLACE VIEW v_daily_volume_by_exchange AS
SELECT 
    DATE(timestamp) as trade_date,
    exchange,
    symbol,
    SUM(volume) as total_volume,
    COUNT(*) as bar_count,
    AVG(close) as avg_price
FROM market_data_seconds
WHERE timestamp >= CURRENT_DATE
GROUP BY DATE(timestamp), exchange, symbol
ORDER BY trade_date DESC, total_volume DESC;

-- =====================================================
-- FUNCTIONS FOR DATA QUALITY
-- =====================================================

-- Function to validate OHLC data
CREATE OR REPLACE FUNCTION validate_ohlc(
    p_open DECIMAL,
    p_high DECIMAL, 
    p_low DECIMAL,
    p_close DECIMAL
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN (
        p_high >= p_open AND 
        p_high >= p_close AND
        p_low <= p_open AND 
        p_low <= p_close AND
        p_high >= p_low AND
        p_open > 0 AND
        p_high > 0 AND
        p_low > 0 AND
        p_close > 0
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get exchange ID by name
CREATE OR REPLACE FUNCTION get_exchange_id(exchange_name_param VARCHAR)
RETURNS INTEGER AS $
DECLARE
    exchange_id_result INTEGER;
BEGIN
    SELECT exchange_id INTO exchange_id_result
    FROM exchanges
    WHERE exchange_name = exchange_name_param;
    
    RETURN COALESCE(exchange_id_result, 1); -- Default to CME if not found
END;
$ LANGUAGE plpgsql STABLE;

-- Function to calculate spread percentage
CREATE OR REPLACE FUNCTION calculate_spread_percentage(
    bid_price DECIMAL,
    ask_price DECIMAL
) RETURNS DECIMAL AS $
BEGIN
    IF bid_price IS NULL OR ask_price IS NULL OR bid_price <= 0 OR ask_price <= 0 THEN
        RETURN NULL;
    END IF;
    
    RETURN ROUND(((ask_price - bid_price) / ((bid_price + ask_price) / 2)) * 100, 4);
END;
$ LANGUAGE plpgsql IMMUTABLE;

-- =====================================================
-- TRIGGERS FOR DATA INTEGRITY
-- =====================================================

-- Trigger to validate OHLC data before insert
CREATE OR REPLACE FUNCTION trigger_validate_market_data()
RETURNS TRIGGER AS $
BEGIN
    -- Validate OHLC relationships
    IF NOT validate_ohlc(NEW.open, NEW.high, NEW.low, NEW.close) THEN
        RAISE EXCEPTION 'Invalid OHLC data: O=%, H=%, L=%, C=%', 
            NEW.open, NEW.high, NEW.low, NEW.close;
    END IF;
    
    -- Calculate spread if bid/ask available
    IF NEW.bid IS NOT NULL AND NEW.ask IS NOT NULL THEN
        NEW.spread = NEW.ask - NEW.bid;
    END IF;
    
    -- Set exchange code if not provided
    IF NEW.exchange_code IS NULL THEN
        SELECT e.exchange_code INTO NEW.exchange_code
        FROM exchanges e
        WHERE e.exchange_name = NEW.exchange;
    END IF;
    
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- Apply trigger to market data tables
CREATE TRIGGER validate_market_data_seconds
    BEFORE INSERT OR UPDATE ON market_data_seconds
    FOR EACH ROW EXECUTE FUNCTION trigger_validate_market_data();

CREATE TRIGGER validate_market_data_minutes  
    BEFORE INSERT OR UPDATE ON market_data_minutes
    FOR EACH ROW EXECUTE FUNCTION trigger_validate_market_data();

-- =====================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- =====================================================

-- Hourly market summary by exchange
CREATE MATERIALIZED VIEW mv_hourly_market_summary AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour_timestamp,
    symbol,
    exchange,
    COUNT(*) as bar_count,
    SUM(volume) as total_volume,
    AVG(close) as avg_price,
    MIN(low) as session_low,
    MAX(high) as session_high,
    FIRST(open ORDER BY timestamp) as session_open,
    LAST(close ORDER BY timestamp) as session_close,
    AVG(spread) as avg_spread,
    STDDEV(close) as price_volatility
FROM market_data_seconds
GROUP BY DATE_TRUNC('hour', timestamp), symbol, exchange
ORDER BY hour_timestamp DESC, symbol, exchange;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_hourly_summary_time ON mv_hourly_market_summary (hour_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mv_hourly_summary_symbol ON mv_hourly_market_summary (symbol, hour_timestamp DESC);

-- Exchange performance summary
CREATE MATERIALIZED VIEW mv_exchange_performance AS
SELECT 
    DATE(timestamp) as trade_date,
    exchange,
    COUNT(DISTINCT symbol) as symbols_traded,
    COUNT(DISTINCT contract) as contracts_traded,
    SUM(volume) as total_volume,
    AVG(spread) as avg_spread,
    COUNT(*) as total_bars,
    MIN(timestamp) as first_trade,
    MAX(timestamp) as last_trade
FROM market_data_seconds
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(timestamp), exchange
ORDER BY trade_date DESC, total_volume DESC;

-- =====================================================
-- STORED PROCEDURES FOR COMMON OPERATIONS
-- =====================================================

-- Procedure to insert second-based market data
CREATE OR REPLACE FUNCTION insert_market_data_second(
    p_timestamp TIMESTAMPTZ,
    p_symbol VARCHAR(10),
    p_contract VARCHAR(10),
    p_exchange VARCHAR(10),
    p_open DECIMAL(12,4),
    p_high DECIMAL(12,4),
    p_low DECIMAL(12,4),
    p_close DECIMAL(12,4),
    p_volume INTEGER DEFAULT 0,
    p_tick_count INTEGER DEFAULT 0,
    p_vwap DECIMAL(12,4) DEFAULT NULL,
    p_bid DECIMAL(12,4) DEFAULT NULL,
    p_ask DECIMAL(12,4) DEFAULT NULL
) RETURNS BOOLEAN AS $
BEGIN
    INSERT INTO market_data_seconds (
        timestamp, symbol, contract, exchange,
        open, high, low, close, volume, tick_count,
        vwap, bid, ask, spread
    ) VALUES (
        p_timestamp, p_symbol, p_contract, p_exchange,
        p_open, p_high, p_low, p_close, p_volume, p_tick_count,
        p_vwap, p_bid, p_ask,
        CASE WHEN p_bid IS NOT NULL AND p_ask IS NOT NULL 
             THEN p_ask - p_bid 
             ELSE NULL END
    )
    ON CONFLICT (timestamp, symbol, contract, exchange) 
    DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        tick_count = EXCLUDED.tick_count,
        vwap = EXCLUDED.vwap,
        bid = EXCLUDED.bid,
        ask = EXCLUDED.ask,
        spread = EXCLUDED.spread,
        created_at = NOW();
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error inserting market data: %', SQLERRM;
        RETURN FALSE;
END;
$ LANGUAGE plpgsql;

-- Procedure to get latest price by exchange
CREATE OR REPLACE FUNCTION get_latest_price(
    p_symbol VARCHAR(10),
    p_exchange VARCHAR(10) DEFAULT NULL
) RETURNS TABLE (
    contract VARCHAR(10),
    exchange VARCHAR(10),
    last_price DECIMAL(12,4),
    timestamp TIMESTAMPTZ,
    volume INTEGER,
    bid DECIMAL(12,4),
    ask DECIMAL(12,4)
) AS $
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (mds.contract, mds.exchange)
        mds.contract,
        mds.exchange,
        mds.close,
        mds.timestamp,
        mds.volume,
        mds.bid,
        mds.ask
    FROM market_data_seconds mds
    WHERE mds.symbol = p_symbol
      AND (p_exchange IS NULL OR mds.exchange = p_exchange)
      AND mds.timestamp >= NOW() - INTERVAL '1 hour'
    ORDER BY mds.contract, mds.exchange, mds.timestamp DESC;
END;
$ LANGUAGE plpgsql STABLE;

-- =====================================================
-- DATA RETENTION POLICIES
-- =====================================================

-- Drop old raw tick data (keep only 7 days)
SELECT add_retention_policy('raw_tick_data', INTERVAL '7 days');

-- Drop old second data (keep 1 year)  
SELECT add_retention_policy('market_data_seconds', INTERVAL '1 year');

-- Drop old minute data (keep 2 years)
SELECT add_retention_policy('market_data_minutes', INTERVAL '2 years');

-- Drop old predictions (keep 6 months)
SELECT add_retention_policy('predictions', INTERVAL '6 months');

-- =====================================================
-- COMPRESSION POLICIES
-- =====================================================

-- Compress market data older than 1 day
SELECT add_compression_policy('market_data_seconds', INTERVAL '1 day');
SELECT add_compression_policy('market_data_minutes', INTERVAL '1 day');
SELECT add_compression_policy('raw_tick_data', INTERVAL '1 hour');

-- =====================================================
-- CONTINUOUS AGGREGATES
-- =====================================================

-- 5-minute aggregates from second data
CREATE MATERIALIZED VIEW market_data_5min
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('5 minutes', timestamp) AS bucket,
    symbol,
    contract,
    exchange,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume,
    SUM(tick_count) AS tick_count,
    AVG(vwap) AS vwap,
    LAST(bid, timestamp) AS bid,
    LAST(ask, timestamp) AS ask,
    AVG(spread) AS avg_spread
FROM market_data_seconds
GROUP BY bucket, symbol, contract, exchange;

-- 15-minute aggregates  
CREATE MATERIALIZED VIEW market_data_15min
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('15 minutes', timestamp) AS bucket,
    symbol,
    contract,
    exchange,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume,
    SUM(tick_count) AS tick_count,
    AVG(vwap) AS vwap,
    LAST(bid, timestamp) AS bid,
    LAST(ask, timestamp) AS ask,
    AVG(spread) AS avg_spread
FROM market_data_seconds
GROUP BY bucket, symbol, contract, exchange;

-- Hourly aggregates
CREATE MATERIALIZED VIEW market_data_1hour
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    symbol,
    contract,
    exchange,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume,
    SUM(tick_count) AS tick_count,
    AVG(vwap) AS vwap,
    LAST(bid, timestamp) AS bid,
    LAST(ask, timestamp) AS ask,
    AVG(spread) AS avg_spread,
    COUNT(*) AS bar_count
FROM market_data_seconds
GROUP BY bucket, symbol, contract, exchange;

-- =====================================================
-- REFRESH POLICIES FOR CONTINUOUS AGGREGATES
-- =====================================================

-- Refresh policies (how often to update the aggregated views)
SELECT add_continuous_aggregate_policy('market_data_5min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

SELECT add_continuous_aggregate_policy('market_data_15min',
    start_offset => INTERVAL '3 hours', 
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

SELECT add_continuous_aggregate_policy('market_data_1hour',
    start_offset => INTERVAL '12 hours',
    end_offset => INTERVAL '15 minutes', 
    schedule_interval => INTERVAL '15 minutes');

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

-- Grant permissions to trading user
GRANT USAGE ON SCHEMA public TO trading_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_user;

-- Grant read-only access to analytics user
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO analytics_user;

-- =====================================================
-- SAMPLE QUERIES FOR TESTING
-- =====================================================

/*
-- Insert sample data
SELECT insert_market_data_second(
    NOW(),
    'NQ',
    'NQZ24', 
    'CME',
    17245.50,
    17246.00,
    17245.25,
    17245.75,
    150,
    12,
    17245.68,
    17245.50,
    17245.75
);

-- Get latest prices
SELECT * FROM get_latest_price('NQ');
SELECT * FROM get_latest_price('ES', 'CME');

-- Query market data with exchange
SELECT 
    timestamp,
    symbol,
    contract,
    exchange,
    close,
    volume,
    spread
FROM market_data_seconds 
WHERE symbol = 'NQ' 
  AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 100;

-- Exchange volume comparison
SELECT 
    exchange,
    SUM(volume) as total_volume,
    COUNT(*) as bar_count,
    AVG(spread) as avg_spread
FROM market_data_seconds
WHERE timestamp >= CURRENT_DATE
  AND symbol IN ('NQ', 'ES')
GROUP BY exchange
ORDER BY total_volume DESC;

-- Active contracts by exchange
SELECT * FROM v_active_contracts 
WHERE symbol IN ('NQ', 'ES')
ORDER BY exchange_name, expiration_date;
*/