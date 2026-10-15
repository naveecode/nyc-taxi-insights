"""Repository paths and the public TLC file names."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLE_DIR = DATA_DIR / "sample"
AGG_DIR = DATA_DIR / "agg"
SQL_DIR = ROOT / "sql"
SITE_DIR = ROOT / "site"
FIGURE_DIR = ROOT / "docs" / "figures"
TMP_DIR = DATA_DIR / "tmp"

SAMPLE_TRIPS = SAMPLE_DIR / "yellow_2024_sample_10k.parquet"
SAMPLE_ZONES = SAMPLE_DIR / "taxi_zone_lookup.csv"
RAW_ZONES = RAW_DIR / "taxi_zone_lookup.csv"
HEADLINES = AGG_DIR / "headlines.json"

TRIP_GLOB_NAME = "yellow_tripdata_2024-*.parquet"
SAMPLE_ROWS = 10_000

QUERY_FILES = (
    "01_data_quality.sql",
    "02_hourly_demand.sql",
    "03_zone_rankings.sql",
    "04_tip_by_payment.sql",
    "05_airport_economics.sql",
    "06_speed_by_hour_borough.sql",
    "07_anomaly_rules.sql",
    "08_demand_heatmap.sql",
    "09_monthly_volume.sql",
)

MONTHS = tuple(f"{m:02d}" for m in range(1, 13))
TRIP_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-{month}.parquet"
ZONE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

DOW_NAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
DOW_SHORT = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def trip_parquet_glob() -> str:
    return str(RAW_DIR / TRIP_GLOB_NAME)


def query_stem(filename: str) -> str:
    return filename.removesuffix(".sql")
