import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from database import WEATHER_LOCATION, ensure_schema, fetch_readings, get_engine, latest_reading

load_dotenv()
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Africa/Lagos")
LOCAL_TZ = ZoneInfo(APP_TIMEZONE)
GENERATOR_INTERVAL_SECONDS = max(10, int(os.getenv("GENERATOR_INTERVAL_SECONDS", "20")))

st.set_page_config(page_title="Weather Monitoring & Forecasting", page_icon="🌦️", layout="wide")

st.markdown(
    """
    <style>
        .stApp {
            background: #edf2f7;
            color: #0f172a;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }
        [data-testid="stSidebar"] {
            background: #eaf1f8;
            border-right: 1px solid rgba(148, 163, 184, 0.4);
            padding-top: 0.8rem;
        }
        [data-testid="stSidebarNav"] {
            gap: 0.25rem;
        }
        .sidebar-logo {
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #0f172a;
            margin-bottom: 0.8rem;
        }
        .sidebar-logo small {
            display: block;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            text-transform: none;
            color: #475569;
        }
        .nav-item {
            border-radius: 0.5rem;
            padding: 0.5rem 0.7rem;
            margin: 0.15rem 0.2rem;
            font-weight: 500;
            color: #334155;
        }
        .nav-item:hover {
            background: rgba(148, 163, 184, 0.14);
        }
        .nav-item.active {
            background: #cfe3ff;
            color: #0f172a;
            font-weight: 600;
        }
        .sidebar-status {
            margin-top: 1.2rem;
            padding: 0.75rem 0.5rem 0;
            border-top: 1px solid rgba(148, 163, 184, 0.35);
            color: #334155;
            font-size: 0.92rem;
        }
        .live-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #0f766e;
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .live-dot {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 50%;
            background: #10b981;
            display: inline-block;
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin: 0.2rem 0 1.2rem 0;
            padding: 0.2rem 0.2rem 0.9rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.25);
        }
        .header-title {
            font-size: clamp(2rem, 3vw, 3rem);
            font-weight: 800;
            letter-spacing: -0.05em;
            color: #0f172a;
            margin: 0;
        }
        .header-subtitle {
            color: #475569;
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        .control-panel {
            display: flex;
            align-items: center;
            gap: 0.7rem;
        }
        .field-shell {
            background: rgba(255,255,255,0.5);
            border: 1px solid rgba(148, 163, 184, 0.38);
            border-radius: 0.7rem;
            padding: 0.45rem 0.75rem;
            min-width: 180px;
        }
        .compact-label {
            font-size: 0.72rem;
            color: #64748b;
            margin-bottom: 0.1rem;
            display: block;
        }
        .date-pill {
            background: rgba(255,255,255,0.65);
            border: 1px solid rgba(148,163,184,0.4);
            border-radius: 0.65rem;
            padding: 0.55rem 0.75rem;
            color: #0f172a;
            font-weight: 600;
            min-width: 120px;
            text-align: center;
        }
        .metric-card {
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 0.9rem;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            padding: 0.9rem 1rem;
            min-height: 118px;
        }
        .metric-label {
            color: #475569;
            font-size: 0.82rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.6rem;
        }
        .metric-value {
            font-size: clamp(1.5rem, 2vw, 2.1rem);
            font-weight: 800;
            letter-spacing: -0.04em;
            color: #0f172a;
            margin: 0.1rem 0 0.2rem;
        }
        .metric-delta {
            color: #0f766e;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .metric-delta.negative {
            color: #dc2626;
        }
        .chart-card {
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 0.9rem;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            padding: 0.7rem 0.8rem 0.2rem;
            min-height: 310px;
        }
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.3rem;
            color: #0f172a;
            font-weight: 700;
        }
        .chart-header .icon {
            color: #2563eb;
            font-size: 1.1rem;
        }
        .table-card {
            background: rgba(255,255,255,0.75);
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 0.9rem;
            padding: 0.8rem 0.9rem 0.3rem;
        }
        .section-head {
            font-size: 1.2rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0.5rem 0 0.8rem 0;
        }
        .stButton > button {
            border-radius: 0.7rem;
            border: 1px solid rgba(148,163,184,0.35);
            background: rgba(255,255,255,0.7);
            color: #0f172a;
        }
        .stRadio > div[role="radiogroup"] {
            gap: 0.25rem;
        }
        .stRadio label {
            padding: 0.2rem 0.4rem;
            border-radius: 0.5rem;
        }
        div[data-baseweb="select"] > div {
            border-radius: 0.6rem;
            border: 1px solid rgba(148,163,184,0.4);
            background: rgba(255,255,255,0.7);
        }
        .stDataFrame {
            background: transparent;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_refresh_countdown() -> str:
    remaining = GENERATOR_INTERVAL_SECONDS - int(time.monotonic() % GENERATOR_INTERVAL_SECONDS)
    minutes, seconds = divmod(remaining, 60)
    return f"{minutes:02d}:{seconds:02d}"


@st.cache_resource
def connect_db():
    engine = get_engine()
    ensure_schema(engine)
    return engine


def prepare_window_data(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return frame

    prepared = frame.copy()
    prepared["observed_at"] = pd.to_datetime(prepared["observed_at"], utc=True)
    prepared["observed_local"] = prepared["observed_at"].dt.tz_convert(LOCAL_TZ)
    for column in ["temperature_c", "pressure_hpa", "humidity_pct"]:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared = prepared.sort_values("observed_at").reset_index(drop=True)
    return prepared


def compute_summary_stats(frame: pd.DataFrame) -> dict:
    if frame is None or frame.empty:
        return {
            "count": 0,
            "temperature_min": None,
            "temperature_max": None,
            "temperature_avg": None,
            "pressure_min": None,
            "pressure_max": None,
            "pressure_avg": None,
            "humidity_min": None,
            "humidity_max": None,
            "humidity_avg": None,
        }

    prepared = prepare_window_data(frame)
    return {
        "count": int(len(prepared)),
        "temperature_min": float(prepared["temperature_c"].min()),
        "temperature_max": float(prepared["temperature_c"].max()),
        "temperature_avg": float(prepared["temperature_c"].mean()),
        "pressure_min": float(prepared["pressure_hpa"].min()),
        "pressure_max": float(prepared["pressure_hpa"].max()),
        "pressure_avg": float(prepared["pressure_hpa"].mean()),
        "humidity_min": float(prepared["humidity_pct"].min()),
        "humidity_max": float(prepared["humidity_pct"].max()),
        "humidity_avg": float(prepared["humidity_pct"].mean()),
    }


def calculate_change(current_value: float, previous_value: float | None) -> float | None:
    if previous_value is None:
        return None
    return float(current_value - previous_value)


def build_weather_chart(frame: pd.DataFrame, column: str, title: str, y_label: str):
    chart_data = prepare_window_data(frame)
    if chart_data.empty:
        return None

    fig = px.line(
        chart_data,
        x="observed_local",
        y=column,
        markers=True,
        title=title,
        labels={"observed_local": f"Time ({APP_TIMEZONE})", column: y_label},
    )
    fig.update_layout(
        height=330,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_traces(line=dict(width=2.5), marker=dict(size=6))
    return fig


def render_summary_cards(frame: pd.DataFrame):
    if frame is None or frame.empty:
        st.warning("No readings are available for the currently selected window.")
        return

    prepared = prepare_window_data(frame)
    latest = prepared.iloc[-1]
    previous = prepared.iloc[-2] if len(prepared) > 1 else None

    temp_delta = calculate_change(latest["temperature_c"], previous["temperature_c"] if previous is not None else None)
    pressure_delta = calculate_change(latest["pressure_hpa"], previous["pressure_hpa"] if previous is not None else None)
    humidity_delta = calculate_change(latest["humidity_pct"], previous["humidity_pct"] if previous is not None else None)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Temperature",
            value=f"{latest['temperature_c']:.1f} °C",
            delta=(f"{temp_delta:+.1f} °C" if temp_delta is not None else "No prior reading"),
            delta_color="normal",
        )
    with col2:
        st.metric(
            label="Pressure",
            value=f"{latest['pressure_hpa']:.1f} hPa",
            delta=(f"{pressure_delta:+.1f} hPa" if pressure_delta is not None else "No prior reading"),
            delta_color="normal",
        )
    with col3:
        st.metric(
            label="Humidity",
            value=f"{latest['humidity_pct']:.1f}%",
            delta=(f"{humidity_delta:+.1f}%" if humidity_delta is not None else "No prior reading"),
            delta_color="normal",
        )
    with col4:
        stale_threshold = timedelta(seconds=GENERATOR_INTERVAL_SECONDS * 2)
        latest_timestamp = pd.Timestamp(latest["observed_at"]).to_pydatetime().astimezone(timezone.utc)
        seconds_since = (datetime.now(timezone.utc) - latest_timestamp).total_seconds()
        if seconds_since > stale_threshold.total_seconds():
            st.metric("Next update", "Delayed", delta=f"{int(seconds_since)}s stale")
        else:
            next_update = latest_timestamp + timedelta(seconds=GENERATOR_INTERVAL_SECONDS)
            remaining = max(0, (next_update - datetime.now(timezone.utc)).total_seconds())
            st.metric("Next update", f"{remaining // 60:.0f}m {remaining % 60:.0f}s", delta="On schedule")


def render_summary_statistics(frame: pd.DataFrame):
    stats = compute_summary_stats(frame)
    if stats["count"] == 0:
        st.info("No readings available for the selected time window.")
        return

    st.markdown('<div class="section-header">Summary statistics</div>', unsafe_allow_html=True)
    st.caption(f"Window readings: {stats['count']}")
    metrics = [
        ("Temperature min", stats["temperature_min"], "°C"),
        ("Temperature max", stats["temperature_max"], "°C"),
        ("Temperature avg", stats["temperature_avg"], "°C"),
        ("Pressure min", stats["pressure_min"], "hPa"),
        ("Pressure max", stats["pressure_max"], "hPa"),
        ("Pressure avg", stats["pressure_avg"], "hPa"),
        ("Humidity min", stats["humidity_min"], "%"),
        ("Humidity max", stats["humidity_max"], "%"),
        ("Humidity avg", stats["humidity_avg"], "%"),
    ]

    columns = st.columns(3)
    for idx, (label, value, unit) in enumerate(metrics):
        with columns[idx % 3]:
            if value is not None:
                st.metric(label=label, value=f"{value:.2f} {unit}")


def render_data_table(frame: pd.DataFrame):
    if frame is None or frame.empty:
        st.info("No readings match this time window.")
        return

    prepared = prepare_window_data(frame)
    table = prepared[["observed_local", "temperature_c", "pressure_hpa", "humidity_pct", "source"]].copy()
    table.columns = ["Timestamp", "Temperature (°C)", "Pressure (hPa)", "Humidity (%)", "Source"]
    table = table.sort_values("Timestamp", ascending=False)

    st.dataframe(table, width="stretch", hide_index=True)
    csv_bytes = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download selected window as CSV",
        data=csv_bytes,
        file_name="weather_readings.csv",
        mime="text/csv",
    )


def render_dashboard(engine, location: str):
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(hours=2)
    df = fetch_readings(engine, location, start_utc, now_utc)
    window = prepare_window_data(df)

    if df.empty:
        latest = latest_reading(engine, location)
        st.warning(
            "No readings are available for the last two hours. Confirm the generator is running and writing to the same PostgreSQL database."
        )
        if latest:
            st.caption(f"Latest stored reading: {latest['observed_at']}")
        return

    latest_record = latest_reading(engine, location)
    if latest_record:
        latest_observed = pd.Timestamp(latest_record["observed_at"]).to_pydatetime().astimezone(timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - latest_observed).total_seconds()
        if age_seconds > 2 * GENERATOR_INTERVAL_SECONDS:
            st.warning("Weather data is stale. The latest reading is older than the expected generator interval.")

    st.subheader("Live weather snapshot")
    st.caption(f"Location: {location} • Timezone: {APP_TIMEZONE} • Last refreshed: {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    render_summary_cards(window)

    st.markdown('<div class="section-header">Live monitoring charts</div>', unsafe_allow_html=True)
    chart_columns = st.columns(3)
    for idx, (column, title, y_label) in enumerate([
        ("temperature_c", "Temperature over time", "Temperature (°C)"),
        ("pressure_hpa", "Atmospheric pressure over time", "Pressure (hPa)"),
        ("humidity_pct", "Relative humidity over time", "Humidity (%)"),
    ]):
        with chart_columns[idx]:
            fig = build_weather_chart(window, column, title, y_label)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")

    render_summary_statistics(window)
    render_data_table(window)


def render_historical(engine, location: str):
    now_local = datetime.now(LOCAL_TZ)
    date_col, time_col = st.columns(2)

    with date_col:
        selected_date = st.date_input("Historical date", value=now_local.date(), max_value=now_local.date())
    with time_col:
        selected_time = st.time_input(
            "Window end time",
            value=now_local.time().replace(second=0, microsecond=0),
        )

    end_local = datetime.combine(selected_date, selected_time).replace(tzinfo=LOCAL_TZ)
    start_local = end_local - timedelta(hours=2)

    if end_local > now_local:
        st.warning("The selected end time is in the future; no future readings are available.")

    df = fetch_readings(engine, location, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc))
    window = prepare_window_data(df)

    st.subheader(f"Historical window: {start_local.strftime('%Y-%m-%d %H:%M')} to {end_local.strftime('%Y-%m-%d %H:%M')} ({APP_TIMEZONE})")

    if df.empty:
        st.info("No readings exist for the selected historical window.")
        return

    render_summary_cards(window)

    st.markdown('<div class="section-header">Historical charts</div>', unsafe_allow_html=True)
    chart_columns = st.columns(3)
    for idx, (column, title, y_label) in enumerate([
        ("temperature_c", "Temperature over time", "Temperature (°C)"),
        ("pressure_hpa", "Atmospheric pressure over time", "Pressure (hPa)"),
        ("humidity_pct", "Relative humidity over time", "Humidity (%)"),
    ]):
        with chart_columns[idx]:
            fig = build_weather_chart(window, column, title, y_label)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")

    render_summary_statistics(window)
    render_data_table(window)


def render_dashboard_navigation(engine):
    with st.sidebar:
        st.header("Weather Monitoring & Forecasting")
        st.caption(f"Synthetic readings • {APP_TIMEZONE}")

        location = st.selectbox("Location", [WEATHER_LOCATION], index=0)
        nav = st.radio(
            "Navigation",
            ["Dashboard", "Historical View", "Forecast", "Data Table", "Settings", "About"],
            index=0,
        )

        st.caption(f"Current local time: {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        auto_refresh = st.toggle("Auto-refresh every 20 seconds", value=True)
        st.markdown(
            f"<div style='margin-top: 0.6rem; color: #0f172a;'><span style='font-size:1.2rem;'>⏳</span> <strong>Next refresh</strong> {get_refresh_countdown()}</div>",
            unsafe_allow_html=True,
        )
        if st.button("Refresh now", width="content"):
            st.rerun()

        return location, nav, auto_refresh


def render_settings_panel():
    st.header("Settings")
    st.info("The generator runs as a separate background worker. Streamlit only queries PostgreSQL.")
    st.code(
        "DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME\n"
        "WEATHER_LOCATION=Lagos, Nigeria\n"
        "GENERATOR_INTERVAL_SECONDS=20\n"
        "APP_TIMEZONE=Africa/Lagos\n",
        language="text",
    )


def render_about_panel():
    st.header("About")
    st.markdown(
        """
        This phase uses synthetic weather data only. Readings are generated to model illustrative Nigerian conditions
        and stored in PostgreSQL for monitoring and historical analysis.
        """
    )


def render_data_panel(engine, location: str):
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(hours=2)
    df = fetch_readings(engine, location, start_utc, now_utc)
    window = prepare_window_data(df)
    render_data_table(window)


def main():
    try:
        engine = connect_db()
    except Exception as exc:
        st.error("Could not connect to PostgreSQL. Configure DATABASE_URL in environment variables before starting the dashboard.")
        st.exception(exc)
        st.stop()

    st.title("Weather Monitoring & Forecasting")
    location, nav, auto_refresh = render_dashboard_navigation(engine)

    if nav == "Dashboard":
        if auto_refresh:
            @st.fragment(run_every=20)
            def live_dashboard_fragment():
                render_dashboard(engine, location)

            live_dashboard_fragment()
        else:
            render_dashboard(engine, location)
    elif nav == "Historical View":
        render_historical(engine, location)
    elif nav == "Forecast":
        st.header("Forecast")
        st.info("Forecast functionality is a future Phase 2 feature and is intentionally not implemented in this phase.")
    elif nav == "Data Table":
        render_data_panel(engine, location)
    elif nav == "Settings":
        render_settings_panel()
    elif nav == "About":
        render_about_panel()


if __name__ == "__main__":
    main()
