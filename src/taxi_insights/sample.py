"""Build the committed 10k-row sample used by tests and the notebooks."""

from __future__ import annotations

import shutil

import duckdb

from taxi_insights.paths import (
    RAW_ZONES,
    SAMPLE_ROWS,
    SAMPLE_TRIPS,
    SAMPLE_ZONES,
    trip_parquet_glob,
)


def build_sample() -> None:
    """Draw a seeded reservoir sample from the raw Parquet files."""
    if not RAW_ZONES.exists():
        raise FileNotFoundError(f"Missing {RAW_ZONES}. Run `make data` first.")
    SAMPLE_TRIPS.parent.mkdir(parents=True, exist_ok=True)
    source = trip_parquet_glob().replace("'", "''")
    destination = str(SAMPLE_TRIPS).replace("'", "''")
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
            SELECT *
            FROM read_parquet('{source}', union_by_name = true)
            USING SAMPLE {SAMPLE_ROWS} ROWS (reservoir, 42)
        ) TO '{destination}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{destination}')").fetchone()
    if count is None or count[0] != SAMPLE_ROWS:
        raise RuntimeError(f"Expected {SAMPLE_ROWS} sample rows, found {count}")
    shutil.copyfile(RAW_ZONES, SAMPLE_ZONES)
    print(f"wrote {SAMPLE_TRIPS} ({SAMPLE_ROWS} rows)")
    print(f"wrote {SAMPLE_ZONES}")


def main() -> None:
    build_sample()


if __name__ == "__main__":
    main()
