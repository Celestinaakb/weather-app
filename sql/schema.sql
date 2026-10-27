CREATE TABLE IF NOT EXISTS weather_readings (
    id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL,
    location VARCHAR(120) NOT NULL,
    temperature_c NUMERIC(5, 2) NOT NULL,
    pressure_hpa NUMERIC(7, 2) NOT NULL,
    humidity_pct NUMERIC(5, 2) NOT NULL CHECK (humidity_pct BETWEEN 0 AND 100),
    source VARCHAR(20) NOT NULL DEFAULT 'simulated'
        CHECK (source IN ('simulated', 'observed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT weather_location_timestamp_unique UNIQUE (location, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_weather_location_observed_at
    ON weather_readings (location, observed_at DESC);
