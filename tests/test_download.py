"""URL builders stay pointed at the public TLC files."""

import pytest

from taxi_insights.download import trip_destination, trip_url
from taxi_insights.paths import MONTHS, TRIP_URL, ZONE_URL


def test_twelve_months() -> None:
    assert len(MONTHS) == 12
    assert MONTHS[0] == "01"
    assert MONTHS[-1] == "12"


def test_trip_url_uses_the_public_cloudfront_path() -> None:
    assert trip_url("06") == TRIP_URL.format(month="06")
    assert trip_url("06").startswith("https://d37ci6vzurychx.cloudfront.net/trip-data/")
    assert trip_destination("06").name == "yellow_tripdata_2024-06.parquet"


def test_zone_lookup_is_the_public_csv() -> None:
    assert ZONE_URL.endswith("/misc/taxi_zone_lookup.csv")


def test_unknown_month_is_rejected() -> None:
    with pytest.raises(ValueError):
        trip_url("13")
