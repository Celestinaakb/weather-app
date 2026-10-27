import os
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "Lagos, Nigeria").strip()


def _require_database_url() -> str:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Copy .env.example to .env and configure a PostgreSQL connection string."
        )
    return database_url


def _ensure_tz_aware_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a timezone-aware datetime object.")
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone information.")
    return value.astimezone(timezone.utc)


def get_engine() -> Engine:
    database_url = _require_database_url()
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=1800, future=True)


def _schema_statements(engine: Engine):
    dialect_name = engine.dialect.name

    if dialect_name == "postgresql":
        return (
            """
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
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_weather_location_observed_at
                ON weather_readings (location, observed_at DESC);
            """,
        )

    if dialect_name == "sqlite":
        return (
            """
            CREATE TABLE IF NOT EXISTS weather_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TIMESTAMP NOT NULL,
                location VARCHAR(120) NOT NULL,
                temperature_c NUMERIC(5, 2) NOT NULL,
                pressure_hpa NUMERIC(7, 2) NOT NULL,
                humidity_pct NUMERIC(5, 2) NOT NULL CHECK (humidity_pct BETWEEN 0 AND 100),
                source VARCHAR(20) NOT NULL DEFAULT 'simulated'
                    CHECK (source IN ('simulated', 'observed')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (location, observed_at)
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_weather_location_observed_at
                ON weather_readings (location, observed_at DESC);
            """,
        )

    raise RuntimeError(f"Unsupported database dialect for schema creation: {dialect_name}")


def ensure_schema(engine: Engine) -> None:
    schema_statements = _schema_statements(engine)
    try:
        with engine.begin() as conn:
            for statement in schema_statements:
                conn.execute(text(statement))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"Database schema creation failed for dialect '{engine.dialect.name}'. Check the database configuration and connectivity."
        ) from exc


def insert_reading(
    engine: Engine,
    observed_at: datetime,
    location: str,
    temperature_c,
    pressure_hpa,
    humidity_pct,
    source: str = "simulated",
) -> bool:
    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string.")

    observed_at = _ensure_tz_aware_utc(observed_at, "observed_at")
    temperature = float(temperature_c)
    pressure = float(pressure_hpa)
    humidity = float(humidity_pct)

    if not 0 <= humidity <= 100:
        raise ValueError("humidity_pct must be between 0 and 100.")

    sql = text(
        """
        INSERT INTO weather_readings
            (observed_at, location, temperature_c, pressure_hpa, humidity_pct, source)
        VALUES
            (:observed_at, :location, :temperature_c, :pressure_hpa, :humidity_pct, :source)
        ON CONFLICT (location, observed_at) DO NOTHING
        """
    )

    try:
        with engine.begin() as conn:
            result = conn.execute(
                sql,
                {
                    "observed_at": observed_at,
                    "location": location,
                    "temperature_c": round(temperature, 2),
                    "pressure_hpa": round(pressure, 2),
                    "humidity_pct": round(humidity, 2),
                    "source": source,
                },
            )
        return result.rowcount == 1
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database insert failed. Check DATABASE_URL, PostgreSQL connectivity, and the weather_readings schema."
        ) from exc


def fetch_readings(engine: Engine, location: str, start, end) -> pd.DataFrame:
    if start is None or end is None:
        raise ValueError("start and end must be timezone-aware datetimes.")

    start_utc = _ensure_tz_aware_utc(start, "start")
    end_utc = _ensure_tz_aware_utc(end, "end")
    if start_utc >= end_utc:
        raise ValueError("start must be earlier than end.")

    sql = text(
        """
        SELECT observed_at, location, temperature_c, pressure_hpa, humidity_pct, source
        FROM weather_readings
        WHERE location = :location AND observed_at >= :start AND observed_at < :end
        ORDER BY observed_at ASC
        """
    )

    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                sql,
                conn,
                params={"location": location, "start": start_utc, "end": end_utc},
            )
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database query failed while fetching readings. Check PostgreSQL connectivity and the query parameters."
        ) from exc

    if not df.empty:
        df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
        for column in ["temperature_c", "pressure_hpa", "humidity_pct"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def latest_reading(engine: Engine, location: str):
    sql = text(
        """
        SELECT observed_at, temperature_c, pressure_hpa, humidity_pct, source
        FROM weather_readings
        WHERE location = :location
        ORDER BY observed_at DESC LIMIT 1
        """
    )

    try:
        with engine.connect() as conn:
            row = conn.execute(sql, {"location": location}).mappings().first()
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database query failed while fetching the latest reading. Check PostgreSQL connectivity."
        ) from exc

    return dict(row) if row else None
