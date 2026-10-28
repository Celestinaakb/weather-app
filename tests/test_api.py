from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from weather_app import api
from weather_app.database import ensure_schema


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    ensure_schema(engine)
    monkeypatch.setattr(api, "get_engine", lambda: engine)
    monkeypatch.setenv("API_KEY", "secret")
    with TestClient(api.app) as test_client:
        yield test_client


PAYLOAD = {"temperature_c": 28.4, "pressure_hpa": 1008.2, "humidity_pct": 71.0}
AUTH = {"X-API-Key": "secret"}


def test_post_requires_api_key(client):
    assert client.post("/api/readings", json=PAYLOAD).status_code == 401
    assert client.post("/api/readings", json=PAYLOAD, headers={"X-API-Key": "nope"}).status_code == 401


def test_post_then_read_back(client):
    response = client.post("/api/readings", json=PAYLOAD, headers=AUTH)
    assert response.status_code == 201
    assert response.json()["inserted"] is True

    latest = client.get("/api/readings/latest").json()
    assert latest["temperature_c"] == 28.4
    assert latest["source"] == "observed"

    rows = client.get("/api/readings").json()
    assert len(rows) == 1
    assert client.get("/api/readings", params={"source": "simulated"}).json() == []


def test_rejects_out_of_range_values(client):
    bad = {**PAYLOAD, "humidity_pct": 140}
    assert client.post("/api/readings", json=bad, headers=AUTH).status_code == 422


def test_latest_404_when_empty(client):
    assert client.get("/api/readings/latest").status_code == 404


def test_window_validation(client):
    now = datetime.now(timezone.utc)
    params = {"start": now.isoformat(), "end": (now - timedelta(hours=1)).isoformat()}
    assert client.get("/api/readings", params=params).status_code == 422


def test_dashboard_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Weather Monitor" in response.text
