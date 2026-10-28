"""HTTP client the Streamlit dashboard uses to talk to the FastAPI server."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT_SECONDS = 15


class ApiError(RuntimeError):
    pass


def _get(path: str, **params):
    params = {k: v for k, v in params.items() if v is not None}
    try:
        response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach the weather API at {API_BASE_URL}: {exc}") from exc
    if response.status_code == 404:
        return None
    if not response.ok:
        raise ApiError(f"Weather API returned {response.status_code}: {response.text[:200]}")
    return response.json()


def check_health() -> None:
    _get("/api/health")


def get_config() -> dict[str, Any]:
    config = _get("/api/config")
    if not isinstance(config, dict):
        raise ApiError("Weather API returned an invalid configuration response.")
    return config


def fetch_readings(location: str, start, end) -> pd.DataFrame:
    rows = _get("/api/readings", location=location, start=start.isoformat(), end=end.isoformat())
    frame = pd.DataFrame(rows or [], columns=["observed_at", "temperature_c", "pressure_hpa", "humidity_pct", "source"])
    if not frame.empty:
        frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True)
    return frame


def latest_reading(location: str):
    row = _get("/api/readings/latest", location=location)
    if row is not None:
        row["observed_at"] = pd.to_datetime(row["observed_at"], utc=True)
    return row
