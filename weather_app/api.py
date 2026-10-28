"""FastAPI server: ingest endpoint for the ESP32, read endpoints for the dashboards."""

from __future__ import annotations

import hmac
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from weather_app.database import WEATHER_LOCATION, ensure_schema, fetch_readings, get_engine, insert_reading, latest_reading

load_dotenv()
log = logging.getLogger("weather-api")

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Africa/Lagos")
GENERATOR_INTERVAL_SECONDS = max(10, int(os.getenv("GENERATOR_INTERVAL_SECONDS", "120")))
MAX_WINDOW = timedelta(days=7)
WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    ensure_schema(engine)
    app.state.engine = engine
    if not os.getenv("API_KEY", "").strip():
        log.warning("API_KEY is not set; POST /api/readings accepts unauthenticated requests.")
    yield
    engine.dispose()


app = FastAPI(title="Weather Monitoring API", lifespan=lifespan)


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("API_KEY", "").strip()
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")


class ReadingIn(BaseModel):
    temperature_c: float = Field(ge=-60, le=100)
    pressure_hpa: float = Field(ge=300, le=1100)
    humidity_pct: float = Field(ge=0, le=100)
    location: Optional[str] = Field(default=None, min_length=1, max_length=120)
    # The ESP32 has no real-time clock, so the server stamps the reading unless a time is supplied.
    observed_at: Optional[datetime] = None
    source: Literal["observed", "simulated"] = "observed"


def _iso(value) -> str:
    return pd.to_datetime(value, utc=True).isoformat()


def _serialize_frame(frame) -> list[dict]:
    if frame.empty:
        return []
    return [
        {
            "observed_at": _iso(row.observed_at),
            "temperature_c": float(row.temperature_c),
            "pressure_hpa": float(row.pressure_hpa),
            "humidity_pct": float(row.humidity_pct),
            "source": row.source,
        }
        for row in frame.itertuples(index=False)
    ]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "location": WEATHER_LOCATION,
        "timezone": APP_TIMEZONE,
        "interval_seconds": GENERATOR_INTERVAL_SECONDS,
    }


@app.post("/api/readings", status_code=201, dependencies=[Depends(require_api_key)])
def create_reading(reading: ReadingIn):
    observed_at = reading.observed_at or datetime.now(timezone.utc).replace(microsecond=0)
    if observed_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="observed_at must include timezone information.")
    if observed_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="observed_at is in the future.")

    location = reading.location or WEATHER_LOCATION
    try:
        inserted = insert_reading(
            app.state.engine,
            observed_at,
            location,
            reading.temperature_c,
            reading.pressure_hpa,
            reading.humidity_pct,
            source=reading.source,
        )
    except RuntimeError as exc:
        log.exception("Insert failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"inserted": inserted, "observed_at": _iso(observed_at.astimezone(timezone.utc)), "location": location}


@app.get("/api/readings")
def list_readings(
    location: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    source: Optional[Literal["observed", "simulated"]] = None,
):
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(hours=2)
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(status_code=422, detail="start and end must include timezone information.")
    if start >= end:
        raise HTTPException(status_code=422, detail="start must be earlier than end.")
    if end - start > MAX_WINDOW:
        raise HTTPException(status_code=422, detail="Requested window is longer than 7 days.")

    try:
        frame = fetch_readings(app.state.engine, location or WEATHER_LOCATION, start, end)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if source:
        frame = frame[frame["source"] == source]
    return _serialize_frame(frame)


@app.get("/api/readings/latest")
def get_latest(location: Optional[str] = None):
    try:
        row = latest_reading(app.state.engine, location or WEATHER_LOCATION)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="No readings stored yet.")
    return {
        "observed_at": _iso(row["observed_at"]),
        "temperature_c": float(row["temperature_c"]),
        "pressure_hpa": float(row["pressure_hpa"]),
        "humidity_pct": float(row["humidity_pct"]),
        "source": row["source"],
    }


@app.get("/", include_in_schema=False)
def html_dashboard():
    return FileResponse(WEB_DIR / "index.html")
