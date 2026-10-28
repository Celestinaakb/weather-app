# Weather Monitoring & Forecasting Dashboard

A cloud-ready Python project that simulates weather readings, stores them in PostgreSQL, and visualizes live and historical readings in Streamlit.

**Important:** Initial values are synthetic. This is a monitoring/data-pipeline prototype, not real weather or a validated forecasting model.

## Architecture

- `weather_simulator.py`: creates gradual synthetic temperature, pressure, and humidity values.
- `weather_generator.py`: standalone process; writes a reading immediately and then every 20 seconds.
- `database.py`: PostgreSQL connection, schema setup, insert and query helpers.
- `app.py`: Streamlit dashboard, three time-series charts, live refresh, date/time historical navigation.
- `sql/schema.sql`: database schema.

## Run locally

Requires Python 3.11+ and PostgreSQL.

1. Create a PostgreSQL database named `weatherdb`.
2. Create a virtual environment and install packages:
   ```bash
   python -m venv .venv
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your database URL.
4. In terminal 1 run `python weather_generator.py`.
5. In terminal 2 run `streamlit run app.py`.

The table is created automatically by either process. The generator writes one record immediately, then repeats every two minutes.

## Environment variables

- `DATABASE_URL`: PostgreSQL SQLAlchemy URL, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`
- `WEATHER_LOCATION`: label used to group readings, default `Lagos, Nigeria`
- `GENERATOR_INTERVAL_SECONDS`: default `20`
- `APP_TIMEZONE`: default `Africa/Lagos`
- `SIMULATION_SEED`: optional integer for repeatable synthetic values

## Cloud deployment

Deploy three resources:

1. Managed PostgreSQL database.
2. One always-on background worker running `python weather_generator.py`.
3. Streamlit web service running `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.

Set `DATABASE_URL`, `WEATHER_LOCATION`, and `APP_TIMEZONE` for both services. Keep credentials in platform environment variables, never commit `.env`. Use the provider's private database URL when supported. The `render.yaml` file is a starting point for platforms supporting Render Blueprints; provision/configure PostgreSQL separately as required by your host.

**Only run one generator worker.** Multiple replicas would generate overlapping records. A unique constraint on `(location, observed_at)` prevents exact duplicate timestamps, but it does not replace single-worker deployment.

## Historical view

Live mode shows the latest two hours. Historical mode selects a date and an end time and queries the two-hour period ending at that time. Timestamps are stored as timezone-aware values and displayed in `APP_TIMEZONE`.

## Next: forecasting

After collecting enough records, define a prediction horizon (e.g. temperature 30 minutes ahead). Establish a persistence baseline, then compare a forecasting model using chronological validation and MAE/RMSE. For credible weather prediction, later use real historical observations; synthetic data is suitable for testing the app and pipeline, not proving real-world forecast accuracy.
