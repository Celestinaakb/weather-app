# PRODUCT REQUIREMENTS DOCUMENT (PRD)
## Weather Monitoring & Forecasting Dashboard
**Phase 1: Synthetic Weather Data Generation and Live Monitoring**

### 1. Project Overview

Build a web-based Weather Monitoring Dashboard using Python, Streamlit, and PostgreSQL. The application will simulate weather readings for selected locations in Nigeria and display the generated data through an interactive dashboard.

The system will generate temperature, atmospheric pressure, and relative humidity readings every two minutes, store them in PostgreSQL, and display them through live time-series charts and historical views.

**Phase 1 is strictly focused on synthetic data generation, storage, monitoring, and visualisation.** Real weather API integration and machine learning forecasting will be implemented in later phases.

### 2. Project Objectives

The application must:

- Generate simulated weather readings automatically every two minutes.
- Simulate plausible weather variations for Nigerian locations.
- Persist readings in PostgreSQL for historical analysis.
- Display the latest readings through summary cards.
- Visualise temperature, pressure, and humidity against time.
- Automatically refresh the live dashboard.
- Allow users to browse historical readings by date and time.
- Provide a clean, responsive, professional interface.
- Establish a modular architecture that supports future machine learning integration.

### 3. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Frontend and dashboard | Streamlit |
| Database | PostgreSQL |
| Data manipulation | Pandas |
| Interactive visualisations | Plotly |
| Database access | SQLAlchemy with psycopg |
| Configuration | Environment variables and python-dotenv |
| Deployment | Cloud-hosted web application, background worker, managed PostgreSQL |

Use supported, compatible package versions and record dependencies in `requirements.txt`.

### 4. Data Generation Requirements

Create an independent Python process responsible for generating and storing weather readings.

The generator must:

1. Generate one reading immediately after startup.
2. Generate subsequent readings every 120 seconds.
3. Generate the following measurements:
   - Temperature in degrees Celsius (°C).
   - Atmospheric pressure in hectopascals (hPa).
   - Relative humidity as a percentage (%).
4. Attach a timezone-aware UTC timestamp to every reading.
5. Associate each reading with a location, initially Lagos, Nigeria.
6. Insert each reading into PostgreSQL.
7. Log successful insertions and database errors.
8. Handle shutdown signals gracefully.
9. Prevent duplicate records for the same location and timestamp.
10. Continue operating independently of whether the Streamlit dashboard is open.

Use a time-dependent simulation algorithm rather than generating every measurement independently from a random distribution.

The simulator should include gradual changes, bounded random variation, and a daily temperature pattern. Humidity may respond inversely to temperature within reasonable limits, while pressure changes gradually.

Initial simulation ranges may be configured as follows:

- Temperature: 22–36°C.
- Pressure: 990–1020 hPa.
- Relative humidity: 35–98%.

These are illustrative simulation parameters, not universal weather limits or verified observations. Keep the generator configurable so other Nigerian locations can be added later.

All generated readings must be labelled as **SIMULATED** throughout the application.

### 5. Database Requirements

Create a PostgreSQL table named `weather_readings` with the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | BIGSERIAL PRIMARY KEY | Unique reading identifier |
| `observed_at` | TIMESTAMPTZ | Timestamp of the simulated observation |
| `location` | VARCHAR(120) | Location associated with the reading |
| `temperature_c` | NUMERIC(5,2) | Temperature in Celsius |
| `pressure_hpa` | NUMERIC(7,2) | Atmospheric pressure in hPa |
| `humidity_pct` | NUMERIC(5,2) | Relative humidity percentage |
| `source` | VARCHAR(20) | Data source, initially `simulated` |
| `created_at` | TIMESTAMPTZ | Database insertion timestamp |

Database requirements:

- Create a unique constraint on `(location, observed_at)`.
- Add an index on `(location, observed_at)` for efficient time-range queries.
- Enforce valid humidity percentages between 0 and 100.
- Use parameterised queries.
- Keep database credentials in environment variables.
- Use SQLAlchemy connection management and handle connection errors.
- Store timestamps in UTC and display them in the `Africa/Lagos` timezone by default.

### 6. Dashboard Design and User Interface

Create a modern, clean, light-themed dashboard inspired by professional weather analytics platforms.

**Visual identity:**
- Primary accent: blue.
- Background: light gray.
- Cards and panels: white.
- Text: dark navy or charcoal.
- Secondary elements: muted gray.
- Use subtle borders, restrained shadows, rounded cards, consistent spacing, and clear typography.
- Avoid excessive gradients, decorative elements, and visual clutter.

The interface must have a persistent sidebar navigation menu containing:

1. Dashboard
2. Historical View
3. Forecast — placeholder for a future phase
4. Data Table
5. Settings
6. About

The active navigation item must be visually distinct.

#### 6.1 Dashboard Header

Display:
- Application title: **Weather Monitoring & Forecasting**
- Selected location.
- Current local date and time.
- Live/simulated data status.
- Last successful reading timestamp.

#### 6.2 Summary KPI Cards

Display four cards:

**Temperature**
- Latest temperature in °C.
- Change from the previous reading, where available.
- Optional two-hour minimum and maximum.

**Atmospheric Pressure**
- Latest pressure in hPa.
- Change from the previous reading.

**Humidity**
- Latest relative humidity in %.
- Change from the previous reading.

**Next Update**
- Expected next reading time or countdown.
- Standard generation interval of two minutes.
- A clear indication if readings are delayed.

Changes must be calculated from stored readings, not invented.

#### 6.3 Live Monitoring Charts

Display three separate interactive line charts in a clear, balanced layout.

**Chart 1: Temperature over Time**
- X-axis: timestamp.
- Y-axis: temperature (°C).
- Display readings from the latest two hours.
- Include tooltips and readable time labels.

**Chart 2: Atmospheric Pressure over Time**
- X-axis: timestamp.
- Y-axis: pressure (hPa).
- Display readings from the latest two hours.

**Chart 3: Relative Humidity over Time**
- X-axis: timestamp.
- Y-axis: relative humidity (%).
- Display readings from the latest two hours.

Charts must use actual database query results. Do not hardcode sample chart data into the production dashboard.

#### 6.4 Historical View

Allow users to select a historical date and time.

The application must:
- Provide a date picker.
- Provide a time selector.
- Retrieve the two-hour window ending at the selected time.
- Display the same three charts for the selected window.
- Display the associated readings table.
- Show a helpful message when no readings exist.
- Support navigation to earlier dates and times.

Historical navigation must query existing database records. It must not generate artificial historical readings on demand.

#### 6.5 Latest Readings Table

Provide a table showing:
- Timestamp.
- Temperature (°C).
- Pressure (hPa).
- Humidity (%).
- Data source.

Sort the latest readings first. Include CSV export for the selected time window.

#### 6.6 Summary Statistics

For the selected two-hour window, calculate:
- Minimum temperature.
- Maximum temperature.
- Average temperature.
- Minimum and maximum pressure.
- Average pressure.
- Minimum and maximum humidity.
- Average humidity.
- Number of readings retrieved.

Clearly distinguish the latest measurement from a calculated average.

### 7. Refresh and Scheduling Behaviour

The background generator must run independently from Streamlit.

The live dashboard should refresh its database queries every 120 seconds by default. Provide a manual refresh option or a refresh control where appropriate.

Do not place an endless data-generation loop inside the Streamlit application. Streamlit reruns must not create duplicate generator processes or insert duplicate readings.

The dashboard should show a data freshness indicator based on the timestamp of the latest reading. If the generator stops, display a warning instead of implying that the data is current.

### 8. System Architecture

Implement three independent logical components:

**Component A — Weather Simulator and Generator**
- Generates synthetic weather values.
- Schedules readings every two minutes.
- Validates and inserts readings into PostgreSQL.

**Component B — PostgreSQL Database**
- Stores readings persistently.
- Supports time-range queries and historical analysis.
- Enforces data constraints and uniqueness.

**Component C — Streamlit Dashboard**
- Retrieves stored readings.
- Displays KPIs, charts, historical views, and data tables.
- Refreshes independently of the generator.

The database is the single source of truth for displayed observations.

### 9. Recommended Project Structure

```text
weather-monitoring-forecasting/
├── app.py
├── weather_generator.py
├── weather_simulator.py
├── database.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── sql/
│   └── schema.sql
├── tests/
│   ├── test_simulator.py
│   └── test_database.py
└── .streamlit/
    └── config.toml
```

Keep simulation logic, database access, scheduling, and UI rendering in separate modules. Avoid placing the entire application in one Python file.

### 10. Cloud Deployment Requirements

Deploy the application using three resources:

1. A managed PostgreSQL database.
2. A continuously running background worker executing `python weather_generator.py`.
3. A Streamlit web service executing `streamlit run app.py` with the host and port configured for the deployment platform.

Configure the same database connection and location variables for the worker and web service.

The deployment must:
- Keep credentials outside the source repository.
- Support persistent database storage.
- Allow the dashboard to query the database securely.
- Run only one generator worker unless coordination or locking is implemented.
- Include logging and a clear startup error when required configuration is missing.
- Include deployment and local setup instructions in the README.

### 11. Error Handling and Data Quality

Implement appropriate handling for:
- Missing environment variables.
- Database connection failures.
- Insert failures.
- Empty historical queries.
- Invalid date/time selections.
- Stale or delayed readings.
- Duplicate observations.
- Unexpected simulator values.

Never display a successful update status unless a successful reading has actually been stored or retrieved.

### 12. Testing and Acceptance Criteria

Phase 1 is complete when:

1. The generator writes an initial reading successfully.
2. New readings are inserted approximately every 120 seconds.
3. All required measurements and timestamps are stored correctly.
4. Database constraints prevent duplicate location/timestamp records.
5. The dashboard displays the latest stored measurements.
6. All three charts show database-backed readings from the latest two hours.
7. The dashboard refreshes without starting another generator.
8. Historical date/time selection retrieves the correct two-hour window.
9. Empty windows and database errors produce clear messages.
10. The readings table and CSV export work.
11. The application can be deployed with separate worker, web service, and database resources.
12. All readings are clearly identified as synthetic data.

### 13. Out of Scope for Phase 1

Do not implement the following yet:

- Real weather API integration.
- Machine learning model training.
- Future temperature predictions.
- Automated weather alerts.
- User accounts or role-based access.
- Complex multi-location administration.
- Mobile applications.

The architecture should allow these features to be added in future phases without rebuilding the core system.

### 14. Future Roadmap

**Phase 2 — Forecasting**
- Build a time-series forecasting pipeline.
- Establish a persistence baseline.
- Predict temperature 30, 60, or 120 minutes ahead.
- Evaluate predictions using chronological validation, MAE, and RMSE.
- Display forecasts separately from generated observations.

**Phase 3 — Real Weather Data**
- Integrate a real weather API or observational dataset.
- Preserve source provenance.
- Compare forecasts against actual observations.
- Support additional Nigerian locations.

### 15. Instructions to the AI Development Assistant

Act as a senior Python developer and data engineer.

Implement Phase 1 according to this document.

Before coding:
1. Inspect the existing repository and preserve useful working files.
2. Identify missing components and dependencies.
3. Present a concise implementation plan.

During implementation:
1. Build the database schema and connection layer first.
2. Implement and test the simulator.
3. Implement the independent generator.
4. Implement the Streamlit dashboard.
5. Add historical browsing, charts, and error handling.
6. Add tests, dependency definitions, environment examples, and deployment instructions.
7. Run available tests and fix errors before reporting completion.

Use modular, readable Python with clear function names, type hints where appropriate, parameterised database queries, and secure configuration practices.

Do not replace PostgreSQL with an in-memory database or local-only storage. Do not connect the dashboard directly to an in-process generator. Do not use hardcoded readings as production data. Do not claim that synthetic values represent actual weather.

Deliver working source files, setup instructions, test results, and a clear summary of anything that remains incomplete.
