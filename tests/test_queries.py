"""The SQL library runs on the committed 10k-row sample."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from taxi_insights.db import run_sql
from taxi_insights.paths import QUERY_FILES, SAMPLE_ROWS, SQL_DIR


def _sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def test_sample_has_the_committed_row_count(con: duckdb.DuckDBPyConnection) -> None:
    count = con.execute("SELECT COUNT(*) FROM trips").fetchone()
    assert count is not None
    assert count[0] == SAMPLE_ROWS


def test_population_is_a_subset_of_published_rows(con: duckdb.DuckDBPyConnection) -> None:
    published, kept = con.execute(
        "SELECT (SELECT COUNT(*) FROM trips), (SELECT COUNT(*) FROM population)"
    ).fetchone()
    assert 0 < kept <= published


def test_each_analysis_query_uses_a_cte_and_a_window() -> None:
    for name in QUERY_FILES:
        sql = _sql(name).upper()
        assert "WITH " in sql, name
        assert " OVER " in sql or "\nOVER " in sql or "OVER(" in sql, name
        assert "CREATE " not in sql
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "ATTACH ", "COPY "):
            assert forbidden not in sql, name


def test_population_definition_is_the_kpi_filter() -> None:
    sql = (SQL_DIR / "00_population.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW population" in sql
    assert "pickup_in_2024" in sql
    assert "trip_distance > 0" in sql
    assert "fare_amount > 0" in sql


@pytest.mark.parametrize("name", QUERY_FILES)
def test_query_returns_rows(con: duckdb.DuckDBPyConnection, name: str) -> None:
    frame = run_sql(con, SQL_DIR / name)
    assert len(frame) > 0, name
    assert len(frame.columns) >= 4


def test_hourly_demand_is_a_share_of_the_population(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "02_hourly_demand.sql")
    population = con.execute("SELECT COUNT(*) FROM population").fetchone()[0]
    assert frame["hour"].between(0, 23).all()
    assert frame["trips"].sum() == population
    assert abs(frame["share"].sum() - 1) < 1e-9
    assert frame["demand_rank"].min() == 1
    assert frame["cumulative_share"].max() == pytest.approx(1)


def test_zone_ranks_and_shares(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "03_zone_rankings.sql")
    assert frame["city_rank"].min() == 1
    assert frame["borough_rank"].min() == 1
    assert frame["city_share"].between(0, 1).all()
    assert abs(frame["city_share"].sum() - 1) < 1e-9
    assert frame["cumulative_share"].between(0, 1).all()
    assert "Unknown" not in set(frame["borough"])


def test_tip_rates_stay_in_range(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "04_tip_by_payment.sql")
    assert set(frame["payment_type"]).issuperset({1, 2})
    assert frame["median_tip_pct"].between(0, 1).all()
    assert frame["avg_tip_pct"].between(0, 1.5).all()
    assert frame["pct_with_tip"].between(0, 1).all()
    assert abs(frame["trip_share"].sum() - 1) < 1e-9
    assert frame["tip_rank"].min() == 1


def test_airport_economics_schema(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "05_airport_economics.sql")
    assert {"airport", "product", "direction", "median_fare", "share_of_airport"} <= set(
        frame.columns
    )
    assert frame["median_fare"].gt(0).all()
    assert frame["trips"].gt(0).all()
    assert set(frame["airport"]).issubset({"JFK", "LGA", "EWR"})


def test_speed_is_bounded(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "06_speed_by_hour_borough.sql")
    assert frame["median_speed_mph"].between(0.5, 80).all()
    assert frame["hour"].between(0, 23).all()
    assert frame["slowest_rank"].min() == 1


def test_anomaly_rates(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "07_anomaly_rules.sql")
    assert frame["rule"].is_unique
    assert frame["flag_rate"].between(0, 1).all()
    assert abs(frame["share_of_flags"].sum() - 1) < 1e-9 or frame["flagged"].sum() == 0
    assert frame["severity_rank"].min() == 1
    assert "jfk_flat_off_manhattan" in set(frame["rule"])


def test_data_quality_rates(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "01_data_quality.sql")
    assert frame["flag_rate"].between(0, 1).all()
    assert frame["check_name"].is_unique
    assert "excluded_from_analysis" in set(frame["check_name"])


def test_heatmap_shares_sum_within_each_weekday(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "08_demand_heatmap.sql")
    shares = frame.groupby("pickup_dow")["share_of_dow"].sum()
    assert frame["pickup_dow"].between(0, 6).all()
    assert (shares - 1).abs().max() < 1e-9


def test_monthly_volume_covers_the_sample_year(con: duckdb.DuckDBPyConnection) -> None:
    frame = run_sql(con, SQL_DIR / "09_monthly_volume.sql")
    hourly = run_sql(con, SQL_DIR / "02_hourly_demand.sql")
    assert frame["pickup_month"].between(1, 12).all()
    assert frame["trips"].sum() == hourly["trips"].sum()
    assert abs(frame["share"].sum() - 1) < 1e-9
    assert frame["daily_rate_rank"].min() == 1


def test_sql_files_exist() -> None:
    for name in QUERY_FILES:
        assert Path(SQL_DIR / name).exists()
