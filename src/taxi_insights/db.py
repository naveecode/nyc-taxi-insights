"""DuckDB connection that queries TLC Parquet files in place."""

from __future__ import annotations

from pathlib import Path

import duckdb

from taxi_insights.paths import SQL_DIR, TMP_DIR

ENRICHED_SQL = """
CREATE OR REPLACE VIEW trips_enriched AS
SELECT
    t.VendorID,
    t.tpep_pickup_datetime,
    t.tpep_dropoff_datetime,
    t.passenger_count,
    t.trip_distance,
    t.RatecodeID,
    t.store_and_fwd_flag,
    t.PULocationID,
    t.DOLocationID,
    t.payment_type,
    t.fare_amount,
    t.extra,
    t.mta_tax,
    t.tip_amount,
    t.tolls_amount,
    t.improvement_surcharge,
    t.total_amount,
    t.congestion_surcharge,
    t."Airport_fee" AS airport_fee,
    CAST(t.tpep_pickup_datetime AS DATE) AS pickup_date,
    EXTRACT(year FROM t.tpep_pickup_datetime)::INTEGER AS pickup_year,
    EXTRACT(month FROM t.tpep_pickup_datetime)::INTEGER AS pickup_month,
    EXTRACT(dow FROM t.tpep_pickup_datetime)::INTEGER AS pickup_dow,
    EXTRACT(hour FROM t.tpep_pickup_datetime)::INTEGER AS hour,
    CASE
        WHEN t.tpep_dropoff_datetime > t.tpep_pickup_datetime
        THEN date_diff('second', t.tpep_pickup_datetime, t.tpep_dropoff_datetime)
    END AS duration_sec,
    CASE
        WHEN t.tpep_dropoff_datetime > t.tpep_pickup_datetime
         AND date_diff('second', t.tpep_pickup_datetime, t.tpep_dropoff_datetime) > 0
        THEN t.trip_distance
            / (date_diff('second', t.tpep_pickup_datetime, t.tpep_dropoff_datetime) / 3600.0)
    END AS speed_mph,
    t.tpep_pickup_datetime >= TIMESTAMP '2024-01-01'
        AND t.tpep_pickup_datetime < TIMESTAMP '2025-01-01' AS pickup_in_2024,
    pu.borough AS pu_borough,
    pu.zone AS pu_zone,
    pu.service_zone AS pu_service_zone,
    do_.borough AS do_borough,
    do_.zone AS do_zone,
    CASE t.payment_type
        WHEN 0 THEN 'Not reported'
        WHEN 1 THEN 'Credit card'
        WHEN 2 THEN 'Cash'
        WHEN 3 THEN 'No charge'
        WHEN 4 THEN 'Dispute'
        WHEN 5 THEN 'Unknown'
        WHEN 6 THEN 'Voided'
        ELSE 'Other'
    END AS payment_name,
    CASE t.RatecodeID
        WHEN 1 THEN 'Standard'
        WHEN 2 THEN 'JFK flat'
        WHEN 3 THEN 'Newark'
        WHEN 4 THEN 'Nassau/Westchester'
        WHEN 5 THEN 'Negotiated'
        WHEN 6 THEN 'Group ride'
        WHEN 99 THEN 'Unknown code'
        ELSE 'Other'
    END AS rate_name
FROM trips t
LEFT JOIN zones pu ON t.PULocationID = pu.location_id
LEFT JOIN zones do_ ON t.DOLocationID = do_.location_id
"""


def connect(
    parquet: str | Path,
    zones: str | Path,
    *,
    memory_limit: str = "4GB",
) -> duckdb.DuckDBPyConnection:
    """Open DuckDB and point the `trips` and `zones` views at local files.

    Parquet is read in place. Nothing is loaded into a warehouse.
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memory_limit}'")
    con.execute(f"SET temp_directory = '{TMP_DIR.as_posix()}'")
    con.execute("SET preserve_insertion_order = false")
    parquet_sql = str(parquet).replace("'", "''")
    zones_sql = str(zones).replace("'", "''")
    con.execute(
        f"""
        CREATE VIEW trips AS
        SELECT * FROM read_parquet('{parquet_sql}', union_by_name = true)
        """
    )
    con.execute(
        f"""
        CREATE VIEW zones AS
        SELECT
            CAST(LocationID AS INTEGER) AS location_id,
            Borough AS borough,
            Zone AS zone,
            service_zone
        FROM read_csv('{zones_sql}', header = true)
        """
    )
    attach_views(con)
    return con


def attach_views(con: duckdb.DuckDBPyConnection) -> None:
    """Add `trips_enriched` and `population` on top of existing trips and zones."""
    con.execute(ENRICHED_SQL)
    population_sql = (SQL_DIR / "00_population.sql").read_text(encoding="utf-8")
    con.execute(population_sql)


def run_sql(con: duckdb.DuckDBPyConnection, sql_path: Path):
    """Execute one SELECT file and return a pandas DataFrame."""
    sql = sql_path.read_text(encoding="utf-8")
    return con.execute(sql).df()
