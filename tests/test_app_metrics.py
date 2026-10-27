from datetime import datetime, timezone

import pandas as pd

from app import compute_summary_stats, prepare_window_data


def test_prepare_window_data_converts_times_and_sorts_chronologically():
    frame = pd.DataFrame(
        [
            {
                "observed_at": datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc),
                "temperature_c": 29.5,
                "pressure_hpa": 1012.1,
                "humidity_pct": 68.0,
                "source": "simulated",
            },
            {
                "observed_at": datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc),
                "temperature_c": 28.5,
                "pressure_hpa": 1011.5,
                "humidity_pct": 72.0,
                "source": "simulated",
            },
        ]
    )

    prepared = prepare_window_data(frame)

    assert list(prepared["observed_at"]) == sorted(prepared["observed_at"].tolist())
    assert "observed_local" in prepared.columns
    assert prepared.iloc[0]["temperature_c"] == 28.5


def test_compute_summary_stats_returns_expected_aggregates():
    frame = pd.DataFrame(
        [
            {
                "observed_at": datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc),
                "temperature_c": 29.5,
                "pressure_hpa": 1012.1,
                "humidity_pct": 68.0,
                "source": "simulated",
            },
            {
                "observed_at": datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc),
                "temperature_c": 28.5,
                "pressure_hpa": 1011.5,
                "humidity_pct": 72.0,
                "source": "simulated",
            },
        ]
    )

    stats = compute_summary_stats(frame)

    assert stats["count"] == 2
    assert stats["temperature_min"] == 28.5
    assert stats["temperature_max"] == 29.5
    assert stats["temperature_avg"] == 29.0
    assert stats["pressure_min"] == 1011.5
    assert stats["pressure_max"] == 1012.1
    assert stats["pressure_avg"] == 1011.8
    assert stats["humidity_min"] == 68.0
    assert stats["humidity_max"] == 72.0
    assert stats["humidity_avg"] == 70.0
