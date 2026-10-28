"""Standalone generator process for synthetic weather readings."""

from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

from weather_app.database import ensure_schema, get_engine, insert_reading
from weather_app.simulator import generate_reading

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("weather-generator")

DEFAULT_INTERVAL_SECONDS = 20
DEFAULT_TIMEZONE = "Africa/Lagos"

running = True


def get_interval_seconds() -> int:
    raw_value = os.getenv("GENERATOR_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS)).strip()
    try:
        interval = int(raw_value)
    except (TypeError, ValueError):
        log.warning("Invalid GENERATOR_INTERVAL_SECONDS value %r; using default %s.", raw_value, DEFAULT_INTERVAL_SECONDS)
        return DEFAULT_INTERVAL_SECONDS
    return max(10, interval)


def get_timezone_name() -> str:
    value = os.getenv("APP_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    return value


def get_location_name() -> str:
    from weather_app.database import WEATHER_LOCATION

    value = os.getenv("WEATHER_LOCATION", WEATHER_LOCATION).strip() or WEATHER_LOCATION
    return value


def process_cycle(engine, location: Optional[str] = None, timezone_name: Optional[str] = None) -> bool:
    location_name = location or get_location_name()
    timezone_value = timezone_name or get_timezone_name()
    observed_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    values = generate_reading(observed_at, timezone_value)

    try:
        inserted = insert_reading(engine, observed_at, location_name, **values)
    except Exception:
        log.exception("Database insert failed; will retry on the next scheduled cycle.")
        return False

    if inserted:
        log.info("Inserted synthetic reading at %s for %s: %s", observed_at.isoformat(), location_name, values)
        return True

    log.info("Duplicate synthetic reading skipped for %s at %s.", location_name, observed_at.isoformat())
    return False


def stop_handler(signum, frame):
    global running
    log.info("Shutdown signal received.")
    running = False


def run_generator(
    engine=None,
    *,
    interval_seconds: Optional[int] = None,
    location: Optional[str] = None,
    timezone_name: Optional[str] = None,
    max_cycles: Optional[int] = None,
):
    if engine is None:
        engine = get_engine()

    ensure_schema(engine)

    interval = interval_seconds if interval_seconds is not None else get_interval_seconds()
    location_name = location or get_location_name()
    timezone_value = timezone_name or get_timezone_name()

    log.info("Generating synthetic readings for %s every %s seconds.", location_name, interval)

    if max_cycles is None:
        max_cycles = -1

    cycle_count = 0
    next_run = time.monotonic()

    while running:
        if cycle_count == 0 or max_cycles == -1 or cycle_count < max_cycles:
            process_cycle(engine, location_name, timezone_value)
            cycle_count += 1

        if max_cycles != -1 and cycle_count >= max_cycles:
            break

        next_run += interval
        while running:
            remaining = next_run - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 1))

    return engine


def main():
    global running
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    engine = get_engine()
    try:
        run_generator(engine)
    finally:
        engine.dispose()
        log.info("Generator stopped.")


if __name__ == "__main__":
    main()
