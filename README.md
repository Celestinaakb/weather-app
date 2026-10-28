# Weather Monitoring & Forecasting Dashboard

A cloud-ready Python project that simulates weather readings, stores them in PostgreSQL, and visualizes live and historical readings in Streamlit.

**Important:** Initial values are synthetic. This is a monitoring/data-pipeline prototype, not real weather or a validated forecasting model.

## Architecture
```
weather_app/
  api.py          FastAPI server: ESP32 posts readings here; serves the HTML dashboard at /
  api_client.py   HTTP client used by Streamlit
  dashboard.py    Streamlit dashboard (talks to the API, not the database)
  web/index.html  plain-HTML dashboard (Plotly, no build step)
  database.py     PostgreSQL connection, schema setup, insert and query helpers
  generator.py    standalone synthetic-data process (reading now, then every 120 s)
  simulator.py    gradual synthetic temperature, pressure and humidity values
sql/schema.sql    database schema
tests/
```
Run everything from the repository root.

## Run locally
Requires Python 3.13+ and PostgreSQL.

1. Create a PostgreSQL database named `weatherdb`.
2. Install dependencies with [uv](https://docs.astral.sh/uv/): `uv sync`
3. Copy `.env.example` to `.env` and set your database URL.
4. Run the API: `uv run uvicorn weather_app.api:app --host 0.0.0.0 --port 8000` (`--host 0.0.0.0` lets the ESP32 reach it over the LAN).
5. Open either dashboard:
   - HTML: http://localhost:8000/
   - Streamlit: `uv run python -m streamlit run weather_app/dashboard.py` (uses `API_BASE_URL`, default `http://localhost:8000`)
6. Optional, for synthetic data: `uv run python -m weather_app.generator`.

The ESP32 sketch keeps its ThingSpeak upload/control channel and additionally POSTs each reading to `API_BASE_URL/api/readings`. Set `API_BASE_URL` and `API_KEY` in the sketch.

### API
- `POST /api/readings` (header `X-API-Key`) body `{"temperature_c":..,"pressure_hpa":..,"humidity_pct":..}`; the server timestamps it.
- `GET /api/readings?start=&end=&location=&source=` (default last 2 h), `GET /api/readings/latest`, `GET /api/config`, `GET /api/health`. Interactive docs at `/docs`.

The table is created automatically by either process. The generator writes one record immediately, then repeats every 20 seconds by default.

## Environment variables

- `DATABASE_URL`: PostgreSQL SQLAlchemy URL, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`
- `WEATHER_LOCATION`: label used to group readings, default `Lagos, Nigeria`
- `GENERATOR_INTERVAL_SECONDS`: default `20`
- `API_KEY`: shared secret the ESP32 sends in `X-API-Key`; if unset, ingest is unauthenticated (dev only)
- `API_BASE_URL`: where Streamlit finds the API, default `http://localhost:8000`
- `APP_TIMEZONE`: default `Africa/Lagos`
- `SIMULATION_SEED`: optional integer for repeatable synthetic values

## Cloud deployment
Deploy four resources (the build step on each is `uv sync --frozen --no-dev`, using the committed `uv.lock`):
1. Managed PostgreSQL database.
2. API web service running `uv run --no-sync uvicorn weather_app.api:app --host 0.0.0.0 --port $PORT`.
3. One always-on background worker running `uv run --no-sync python -m weather_app.generator`.
4. Streamlit web service running `uv run --no-sync python -m streamlit run weather_app/dashboard.py --server.port $PORT --server.address 0.0.0.0`.

Set `DATABASE_URL` (and `API_KEY`) on the API and generator, and `API_BASE_URL` (the API's public URL) on Streamlit; `WEATHER_LOCATION` and `APP_TIMEZONE` go on all of them. Keep credentials in platform environment variables, never commit `.env`. Use the provider's private database URL when supported. The `render.yaml` file is a starting point for platforms supporting Render Blueprints; provision/configure PostgreSQL separately as required by your host.

**Only run one generator worker.** Multiple replicas would generate overlapping records. A unique constraint on `(location, observed_at)` prevents exact duplicate timestamps, but it does not replace single-worker deployment.

## Historical view

Live mode shows the latest two hours. Historical mode selects a date and an end time and queries the two-hour period ending at that time. Timestamps are stored as timezone-aware values and displayed in `APP_TIMEZONE`.

## Next: forecasting

After collecting enough records, define a prediction horizon (e.g. temperature 30 minutes ahead). Establish a persistence baseline, then compare a forecasting model using chronological validation and MAE/RMSE. For credible weather prediction, later use real historical observations; synthetic data is suitable for testing the app and pipeline, not proving real-world forecast accuracy.
