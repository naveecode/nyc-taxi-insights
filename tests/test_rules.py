"""Anomaly rules and the KPI filter fire on hand-built rows."""

from __future__ import annotations

import duckdb

from taxi_insights.db import attach_views, run_sql
from taxi_insights.paths import SQL_DIR

EXPECTED_FLAGS = {
    "nonpositive_distance": 1,
    "nonpositive_fare": 1,
    "negative_total": 1,
    "time_inverted": 1,
    "duration_over_3h": 1,
    "speed_over_80": 1,
    "tip_exceeds_fare": 1,
    "passenger_out_of_range": 1,
    "pickup_outside_2024": 1,
    "jfk_flat_off_manhattan": 1,
}


def _connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE zones (
            location_id INTEGER,
            borough VARCHAR,
            zone VARCHAR,
            service_zone VARCHAR
        )
        """
    )
    con.execute(
        """
        INSERT INTO zones VALUES
            (1, 'EWR', 'Newark Airport', 'EWR'),
            (4, 'Manhattan', 'Alphabet City', 'Yellow Zone'),
            (132, 'Queens', 'JFK Airport', 'Airports'),
            (138, 'Queens', 'LaGuardia Airport', 'Airports')
        """
    )
    con.execute(
        """
        CREATE TABLE trips (
            VendorID INTEGER,
            tpep_pickup_datetime TIMESTAMP,
            tpep_dropoff_datetime TIMESTAMP,
            passenger_count BIGINT,
            trip_distance DOUBLE,
            RatecodeID BIGINT,
            store_and_fwd_flag VARCHAR,
            PULocationID INTEGER,
            DOLocationID INTEGER,
            payment_type BIGINT,
            fare_amount DOUBLE,
            extra DOUBLE,
            mta_tax DOUBLE,
            tip_amount DOUBLE,
            tolls_amount DOUBLE,
            improvement_surcharge DOUBLE,
            total_amount DOUBLE,
            congestion_surcharge DOUBLE,
            "Airport_fee" DOUBLE
        )
        """
    )
    rows: list[dict[str, object]] = [
        {},
        {
            "tpep_pickup_datetime": "2023-06-01 10:00:00",
            "tpep_dropoff_datetime": "2023-06-01 10:20:00",
        },
        {"tpep_dropoff_datetime": "2024-06-01 09:00:00"},
        {"trip_distance": 0},
        {"fare_amount": -1, "total_amount": -1, "tip_amount": 0},
        {"tpep_dropoff_datetime": "2024-06-01 14:30:00"},
        {"trip_distance": 30, "tpep_dropoff_datetime": "2024-06-01 10:10:00"},
        {"fare_amount": 10, "tip_amount": 40, "total_amount": 55},
        {"passenger_count": 8},
        {"trip_distance": 120, "tpep_dropoff_datetime": "2024-06-01 12:00:00"},
        {
            "RatecodeID": 2,
            "PULocationID": 132,
            "DOLocationID": 138,
            "trip_distance": 10,
            "fare_amount": 70,
            "total_amount": 90,
            "tpep_dropoff_datetime": "2024-06-01 10:40:00",
        },
        {
            "RatecodeID": 2,
            "PULocationID": 132,
            "DOLocationID": 4,
            "trip_distance": 2,
            "fare_amount": 70,
            "total_amount": 90,
        },
        {
            "payment_type": 0,
            "passenger_count": None,
            "RatecodeID": None,
            "congestion_surcharge": None,
            "Airport_fee": None,
            "tip_amount": 0,
            "fare_amount": 16,
            "total_amount": 18,
        },
    ]
    for overrides in rows:
        _insert(con, overrides)
    attach_views(con)
    return con


def _sql_literal(column: str, value: object) -> str:
    if value is None:
        return "NULL"
    if column.endswith("datetime"):
        return f"TIMESTAMP '{value}'"
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def _insert(con: duckdb.DuckDBPyConnection, overrides: dict[str, object]) -> None:
    row: dict[str, object] = {
        "VendorID": 1,
        "tpep_pickup_datetime": "2024-06-01 10:00:00",
        "tpep_dropoff_datetime": "2024-06-01 10:20:00",
        "passenger_count": 1,
        "trip_distance": 2.0,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 4,
        "DOLocationID": 4,
        "payment_type": 1,
        "fare_amount": 15.0,
        "extra": 0.0,
        "mta_tax": 0.5,
        "tip_amount": 3.0,
        "tolls_amount": 0.0,
        "improvement_surcharge": 1.0,
        "total_amount": 20.0,
        "congestion_surcharge": 2.5,
        "Airport_fee": 0.0,
    }
    row.update(overrides)
    columns = ", ".join(f'"{name}"' if name == "Airport_fee" else name for name in row)
    values = ", ".join(_sql_literal(name, value) for name, value in row.items())
    con.execute(f"INSERT INTO trips ({columns}) VALUES ({values})")


def test_each_anomaly_rule_flags_its_crafted_row() -> None:
    con = _connection()
    frame = run_sql(con, SQL_DIR / "07_anomaly_rules.sql")
    flagged = dict(zip(frame["rule"], frame["flagged"], strict=True))
    assert flagged == EXPECTED_FLAGS
    con.close()


def test_kpi_filter_drops_only_the_broken_rows() -> None:
    con = _connection()
    published, kept = con.execute(
        "SELECT (SELECT COUNT(*) FROM trips), (SELECT COUNT(*) FROM population)"
    ).fetchone()
    assert published == 13
    assert kept == 7
    quality = run_sql(con, SQL_DIR / "01_data_quality.sql").set_index("check_name")
    assert int(quality.loc["excluded_from_analysis", "flagged"]) == 6
    assert int(quality.loc["missing_passenger_count", "flagged"]) == 1
    assert int(quality.loc["missing_rate_code", "flagged"]) == 1
    assert int(quality.loc["payment_not_reported", "flagged"]) == 1
    hourly = run_sql(con, SQL_DIR / "02_hourly_demand.sql")
    assert int(hourly["trips"].sum()) == 7
    con.close()
