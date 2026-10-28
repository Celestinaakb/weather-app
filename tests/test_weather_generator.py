from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from weather_app.generator import get_interval_seconds, process_cycle, run_generator


def _sqlite_engine_stub():
    engine = MagicMock()
    engine.dialect = SimpleNamespace(name="sqlite")
    return engine


def test_get_interval_seconds_uses_default_and_validates_input(monkeypatch):
    monkeypatch.delenv("GENERATOR_INTERVAL_SECONDS", raising=False)
    assert get_interval_seconds() == 120

    monkeypatch.setenv("GENERATOR_INTERVAL_SECONDS", "45")
    assert get_interval_seconds() == 45

    monkeypatch.setenv("GENERATOR_INTERVAL_SECONDS", "bad")
    assert get_interval_seconds() == 120


def test_process_cycle_inserts_initial_reading():
    engine = _sqlite_engine_stub()

    with patch("weather_app.generator.generate_reading") as mock_generate, patch(
        "weather_app.generator.insert_reading", return_value=True
    ) as mock_insert:
        mock_generate.return_value = {
            "temperature_c": 29.5,
            "pressure_hpa": 1012.0,
            "humidity_pct": 63.5,
        }

        inserted = process_cycle(engine, "Lagos, Nigeria", "Africa/Lagos")

    assert inserted is True
    mock_insert.assert_called_once()


def test_run_generator_respects_configuration_and_schedule(monkeypatch):
    engine = _sqlite_engine_stub()
    calls = []
    clock = [0.0]

    def fake_process_cycle(current_engine, location, timezone_name):
        calls.append((location, timezone_name))
        return True

    monkeypatch.setattr("weather_app.generator.process_cycle", fake_process_cycle)
    monkeypatch.setattr("weather_app.generator.running", True)
    monkeypatch.setattr("weather_app.generator.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("weather_app.generator.time.sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    run_generator(engine, interval_seconds=1, location="Lagos, Nigeria", timezone_name="Africa/Lagos", max_cycles=2)

    assert len(calls) == 2
    assert calls[0] == ("Lagos, Nigeria", "Africa/Lagos")


def test_process_cycle_handles_duplicate_insertion():
    engine = _sqlite_engine_stub()

    with patch("weather_app.generator.generate_reading", return_value={
        "temperature_c": 29.2,
        "pressure_hpa": 1012.5,
        "humidity_pct": 64.0,
    }), patch("weather_app.generator.insert_reading", return_value=False):
        inserted = process_cycle(engine, "Lagos, Nigeria", "Africa/Lagos")

    assert inserted is False


def test_process_cycle_handles_database_errors():
    engine = _sqlite_engine_stub()

    with patch("weather_app.generator.generate_reading", return_value={
        "temperature_c": 29.2,
        "pressure_hpa": 1012.5,
        "humidity_pct": 64.0,
    }), patch("weather_app.generator.insert_reading", side_effect=RuntimeError("db unavailable")):
        inserted = process_cycle(engine, "Lagos, Nigeria", "Africa/Lagos")

    assert inserted is False


def test_generator_runs_without_dashboard_dependency():
    engine = _sqlite_engine_stub()
    with patch("weather_app.generator.get_engine", return_value=engine), patch("weather_app.generator.ensure_schema") as mock_schema, patch(
        "weather_app.generator.run_generator"
    ) as mock_run:
        import weather_app.generator as weather_generator

        weather_generator.main()

    mock_schema.assert_not_called()
    mock_run.assert_called_once_with(engine)
