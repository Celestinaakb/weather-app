from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from weather_app.database import ensure_schema, fetch_readings, get_engine, insert_reading, latest_reading


@pytest.fixture
def sqlite_memory_engine():
    return create_engine("sqlite:///:memory:")


def _create_weather_table(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE weather_readings (
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
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_weather_location_observed_at ON weather_readings (location, observed_at DESC);"
            )
        )


def test_database_schema_creation_is_idempotent(sqlite_memory_engine):
    ensure_schema(sqlite_memory_engine)
    ensure_schema(sqlite_memory_engine)

    with sqlite_memory_engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_readings'")
        ).fetchall()
        indexes = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_weather_location_observed_at'"
            )
        ).fetchall()

    assert len(tables) == 1
    assert len(indexes) == 1


def test_insert_and_fetch_readings(sqlite_memory_engine):
    ensure_schema(sqlite_memory_engine)

    now_utc = datetime.now(timezone.utc)
    inserted = insert_reading(
        sqlite_memory_engine,
        now_utc,
        "Lagos, Nigeria",
        29.5,
        1012.25,
        70.1,
    )
    assert inserted is True

    rows = fetch_readings(
        sqlite_memory_engine,
        "Lagos, Nigeria",
        now_utc - timedelta(hours=1),
        now_utc + timedelta(hours=1),
    )

    assert not rows.empty
    assert rows.iloc[0]["location"] == "Lagos, Nigeria"
    assert rows.iloc[0]["temperature_c"] == pytest.approx(29.5)
    assert rows.iloc[0]["pressure_hpa"] == pytest.approx(1012.25)
    assert rows.iloc[0]["humidity_pct"] == pytest.approx(70.1)
    assert rows["observed_at"].dt.tz is not None


def test_duplicate_location_timestamp_is_rejected(sqlite_memory_engine):
    ensure_schema(sqlite_memory_engine)

    timestamp = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    first_insert = insert_reading(
        sqlite_memory_engine,
        timestamp,
        "Lagos, Nigeria",
        28.0,
        1010.0,
        65.0,
    )
    second_insert = insert_reading(
        sqlite_memory_engine,
        timestamp,
        "Lagos, Nigeria",
        29.0,
        1011.0,
        66.0,
    )

    assert first_insert is True
    assert second_insert is False

    rows = fetch_readings(
        sqlite_memory_engine,
        "Lagos, Nigeria",
        timestamp - timedelta(minutes=5),
        timestamp + timedelta(minutes=5),
    )
    assert len(rows) == 1


def test_latest_reading_returns_most_recent_record(sqlite_memory_engine):
    ensure_schema(sqlite_memory_engine)

    first = datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc)
    second = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    insert_reading(sqlite_memory_engine, first, "Lagos, Nigeria", 26.0, 1010.0, 60.0)
    insert_reading(sqlite_memory_engine, second, "Lagos, Nigeria", 31.0, 1008.0, 55.0)

    latest = latest_reading(sqlite_memory_engine, "Lagos, Nigeria")

    assert latest is not None
    assert latest["temperature_c"] == 31.0
    assert latest["humidity_pct"] == 55.0


def test_missing_database_url_raises_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is missing"):
        get_engine()


def test_invalid_humidity_raises_value_error(sqlite_memory_engine):
    ensure_schema(sqlite_memory_engine)
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="humidity_pct must be between 0 and 100"):
        insert_reading(sqlite_memory_engine, timestamp, "Lagos, Nigeria", 29.0, 1012.0, 150.0)


def test_fetch_readings_requires_valid_time_range(sqlite_memory_engine):
    with pytest.raises(ValueError, match="start must be earlier than end"):
        fetch_readings(
            sqlite_memory_engine,
            "Lagos, Nigeria",
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) - timedelta(minutes=5),
        )
