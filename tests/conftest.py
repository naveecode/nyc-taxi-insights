"""Fixtures pointed at the committed sample, never the full TLC download."""

from __future__ import annotations

import duckdb
import pytest

from taxi_insights.db import connect
from taxi_insights.paths import SAMPLE_TRIPS, SAMPLE_ZONES


@pytest.fixture(scope="session")
def con() -> duckdb.DuckDBPyConnection:
    connection = connect(SAMPLE_TRIPS, SAMPLE_ZONES, memory_limit="2GB")
    yield connection
    connection.close()
