"""Run the SQL library against the raw Parquet files and write small CSV extracts."""

from __future__ import annotations

from taxi_insights.db import connect, run_sql
from taxi_insights.paths import (
    AGG_DIR,
    QUERY_FILES,
    RAW_ZONES,
    SQL_DIR,
    query_stem,
    trip_parquet_glob,
)


def aggregate() -> None:
    if not RAW_ZONES.exists():
        raise FileNotFoundError(f"Missing {RAW_ZONES}. Run `make data` first.")
    AGG_DIR.mkdir(parents=True, exist_ok=True)
    con = connect(trip_parquet_glob(), RAW_ZONES)
    for filename in QUERY_FILES:
        frame = run_sql(con, SQL_DIR / filename)
        destination = AGG_DIR / f"{query_stem(filename)}.csv"
        frame.to_csv(destination, index=False)
        print(f"wrote {destination.name} ({len(frame)} rows)")
    con.close()


def main() -> None:
    aggregate()


if __name__ == "__main__":
    main()
