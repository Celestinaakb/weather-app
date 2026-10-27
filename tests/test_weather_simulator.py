from datetime import datetime, timezone

import pytest
from zoneinfo import ZoneInfo

from weather_simulator import generate_reading


@pytest.mark.parametrize(
    "field_name, min_value, max_value",
    [
        ("temperature_c", 22.0, 36.0),
        ("pressure_hpa", 990.0, 1020.0),
        ("humidity_pct", 35.0, 98.0),
    ],
)
def test_generate_reading_returns_required_fields_and_bounds(field_name, min_value, max_value):
    timestamp = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    value = generate_reading(timestamp)

    assert set(value) == {"temperature_c", "pressure_hpa", "humidity_pct"}
    assert min_value <= value[field_name] <= max_value


def test_generate_reading_is_seeded_and_reproducible():
    timestamp = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    original_seed = None
    try:
        import os
        original_seed = os.environ.get("SIMULATION_SEED")
    except Exception:
        original_seed = None

    import weather_simulator as sim

    sim._runtime_rng = None
    sim._state = {"temperature": 29.0, "pressure": 1012.0, "humidity": 72.0}
    sim._seed_value = 42
    sim._rng = sim.random.Random(42)

    first = sim.generate_reading(timestamp)

    sim._runtime_rng = None
    sim._state = {"temperature": 29.0, "pressure": 1012.0, "humidity": 72.0}
    sim._seed_value = 42
    sim._rng = sim.random.Random(42)

    second = sim.generate_reading(timestamp)

    assert first == second

    if original_seed is not None:
        import os
        os.environ["SIMULATION_SEED"] = str(original_seed)


def test_generate_reading_changes_across_daylight_periods():
    morning = datetime(2026, 10, 27, 6, 0, tzinfo=timezone.utc)
    afternoon = datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)

    morning_value = generate_reading(morning)
    afternoon_value = generate_reading(afternoon)

    assert afternoon_value["temperature_c"] > morning_value["temperature_c"]


def test_generate_reading_accepts_timezone_aware_timestamps():
    tz = ZoneInfo("Africa/Lagos")
    local_timestamp = datetime(2026, 10, 27, 9, 30, tzinfo=tz)
    value = generate_reading(local_timestamp.astimezone(timezone.utc))

    assert isinstance(value["temperature_c"], float)
    assert value["pressure_hpa"] >= 990.0
    assert value["humidity_pct"] >= 35.0
