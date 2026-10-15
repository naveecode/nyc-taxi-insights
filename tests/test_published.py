"""Committed full-year extracts, the write-up, and the dashboard agree."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from taxi_insights.paths import AGG_DIR, HEADLINES, ROOT, SITE_DIR

SQL_NAMES = (
    "sql/01_data_quality.sql",
    "sql/02_hourly_demand.sql",
    "sql/03_zone_rankings.sql",
    "sql/04_tip_by_payment.sql",
    "sql/05_airport_economics.sql",
    "sql/06_speed_by_hour_borough.sql",
    "sql/07_anomaly_rules.sql",
    "sql/08_demand_heatmap.sql",
    "sql/09_monthly_volume.sql",
)


def test_population_is_the_same_across_demand_queries() -> None:
    hourly = pd.read_csv(AGG_DIR / "02_hourly_demand.csv")
    monthly = pd.read_csv(AGG_DIR / "09_monthly_volume.csv")
    heatmap = pd.read_csv(AGG_DIR / "08_demand_heatmap.csv")
    assert int(hourly["trips"].sum()) == int(monthly["trips"].sum())
    assert int(hourly["trips"].sum()) == int(heatmap["trips"].sum())


def test_headlines_match_the_extracts() -> None:
    headlines = json.loads(HEADLINES.read_text(encoding="utf-8"))
    hourly = pd.read_csv(AGG_DIR / "02_hourly_demand.csv")
    tips = pd.read_csv(AGG_DIR / "04_tip_by_payment.csv")
    airport = pd.read_csv(AGG_DIR / "05_airport_economics.csv")
    zones = pd.read_csv(AGG_DIR / "03_zone_rankings.csv")
    peak = hourly.loc[hourly["trips"].idxmax()]
    card = tips.loc[tips["payment_type"] == 1].iloc[0]
    flat = airport[
        (airport["airport"] == "JFK")
        & (airport["product"] == "JFK flat")
        & (airport["direction"] == "to Manhattan")
    ].iloc[0]
    top = zones.loc[zones["city_rank"].idxmin()]
    assert headlines["peak_hour"] == int(peak["hour"])
    assert headlines["population_trips"] == int(hourly["trips"].sum())
    assert headlines["card_median_tip_pct"] == float(card["median_tip_pct"])
    assert headlines["jfk_flat_fare"] == float(flat["median_fare"])
    assert headlines["top_zone"] == top["zone"]


def test_dashboard_and_writeup_use_the_headlines() -> None:
    headlines = json.loads(HEADLINES.read_text(encoding="utf-8"))
    page = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    insights = (ROOT / "INSIGHTS.md").read_text(encoding="utf-8")
    assert f'data-peak-hour="{headlines["peak_hour"]}"' in page
    assert f'data-population-trips="{headlines["population_trips"]}"' in page
    assert headlines["top_zone"] in page
    assert headlines["peak_hour_label"] in insights
    assert headlines["top_zone"] in insights
    assert insights.count("**Question.**") == 8
    assert insights.count("**Recommendation.**") == 8
    assert "plotly" in page.lower()
    for name in SQL_NAMES:
        assert name in insights


def test_ci_uses_the_sample_only() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest" in workflow
    assert "ruff" in workflow
    assert "make data" not in workflow
    assert "d37ci6vzurychx" not in workflow
