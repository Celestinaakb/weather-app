"""Synthetic weather readings for illustrative Nigerian conditions.

This module intentionally generates simulated, not real, weather values. It is kept
separate from persistence and scheduling code so it can be reused by a background
worker without coupling to the Streamlit dashboard.
"""

from __future__ import annotations

import math
import os
import random
from datetime import datetime
from typing import Dict, Any
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Africa/Lagos"
DEFAULT_RANGE = {
    "temperature_c": (22.0, 36.0),
    "pressure_hpa": (990.0, 1020.0),
    "humidity_pct": (35.0, 98.0),
}

_seed_value = os.getenv("SIMULATION_SEED")
_rng = random.Random(int(_seed_value)) if _seed_value not in (None, "") else random.Random()
_state = {"temperature": 29.0, "pressure": 1012.0, "humidity": 72.0}


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _get_rng():
    return _rng


def generate_reading(now_utc: datetime, timezone_name: str = DEFAULT_TIMEZONE) -> Dict[str, float]:
    """Return a single synthetic weather reading for the supplied UTC timestamp.

    The output is meant to represent illustrative synthetic conditions for a Nigerian
    location and is intentionally not a real forecast or observed measurement.
    """
    if not isinstance(now_utc, datetime):
        raise TypeError("now_utc must be a timezone-aware datetime object.")
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must include timezone information.")

    local_now = now_utc.astimezone(ZoneInfo(timezone_name))
    hour = local_now.hour + local_now.minute / 60.0

    day_cycle = math.sin(2 * math.pi * ((hour - 9.0) / 24.0))
    target_temperature = 29.0 + 4.0 * day_cycle
    temperature_delta = 0.25 * (target_temperature - _state["temperature"])
    temperature = _state["temperature"] + temperature_delta + _get_rng().uniform(-0.35, 0.35)
    temperature = _clamp(temperature, *DEFAULT_RANGE["temperature_c"])

    pressure_trend = 0.1 * math.sin(2 * math.pi * ((hour - 3.0) / 24.0))
    pressure = _state["pressure"] + pressure_trend + _get_rng().uniform(-0.30, 0.30)
    pressure = _clamp(pressure, *DEFAULT_RANGE["pressure_hpa"])

    humidity_target = 72.0 - 2.5 * (temperature - 28.0)
    humidity_delta = 0.18 * (humidity_target - _state["humidity"])
    humidity = _state["humidity"] + humidity_delta + _get_rng().uniform(-1.5, 1.5)
    humidity = _clamp(humidity, *DEFAULT_RANGE["humidity_pct"])

    _state["temperature"] = temperature
    _state["pressure"] = pressure
    _state["humidity"] = humidity

    return {
        "temperature_c": round(temperature, 2),
        "pressure_hpa": round(pressure, 2),
        "humidity_pct": round(humidity, 2),
    }
