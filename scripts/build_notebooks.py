"""Create the pandas/Plotly notebooks and execute them in-process via nbclient."""

from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from taxi_insights.paths import ROOT

SETUP = """
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
from IPython.display import Image, display

ROOT = Path.cwd()
if not (ROOT / "sql").exists():
    ROOT = ROOT.parent

SAMPLE = ROOT / "data" / "sample" / "yellow_2024_sample_10k.parquet"
ZONES = ROOT / "data" / "sample" / "taxi_zone_lookup.csv"
AGG = ROOT / "data" / "agg"


def show(fig):
    \"\"\"Store a static render so the notebook is readable without the widget.\"\"\"
    display(Image(fig.to_image(format="png", width=960, height=520)))
""".strip()

LOAD = """
trips = duckdb.sql(f"SELECT * FROM read_parquet('{SAMPLE.as_posix()}')").df()
zones = pd.read_csv(ZONES)
trips["pickup"] = pd.to_datetime(trips["tpep_pickup_datetime"])
trips["dropoff"] = pd.to_datetime(trips["tpep_dropoff_datetime"])
trips["duration_sec"] = (trips["dropoff"] - trips["pickup"]).dt.total_seconds()
print(f"{len(trips):,} sample rows, {trips.shape[1]} columns")
trips.head(3)
""".strip()

POPULATION = """
population = trips[
    trips["pickup"].ge("2024-01-01")
    & trips["pickup"].lt("2025-01-01")
    & trips["duration_sec"].between(1, 10800)
    & trips["trip_distance"].gt(0)
    & trips["trip_distance"].le(100)
    & trips["fare_amount"].gt(0)
    & trips["fare_amount"].le(300)
    & trips["total_amount"].gt(0)
].copy()
print(f"{len(population):,} in-policy sample rows of {len(trips):,}")
""".strip()


def _nb(cells: list) -> nbformat.NotebookNode:
    notebook = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "taxi-insights",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
    )
    return notebook


def demand_notebook() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            "# Demand, zones, and speed\n\n"
            "Pandas on the committed 10k-row sample, then the same charts from the "
            "full-year aggregates in `data/agg/`. The SQL behind those aggregates is "
            "in `sql/`. The published numbers are in `INSIGHTS.md`."
        ),
        new_code_cell(SETUP),
        new_markdown_cell("## Sample"),
        new_code_cell(LOAD),
        new_code_cell(POPULATION),
        new_markdown_cell(
            "## Hour of day\n\n"
            "The sample group-by is the same cut as `sql/02_hourly_demand.sql`: "
            "in-policy 2024 trips, counted by pickup hour."
        ),
        new_code_cell(
            """
hourly = (
    population.groupby(population["pickup"].dt.hour)
    .size()
    .rename_axis("hour")
    .reset_index(name="trips")
)
fig = px.bar(
    hourly,
    x="hour",
    y="trips",
    title="Sample: pickups by hour",
    labels={"hour": "Hour", "trips": "Trips"},
)
fig.update_layout(template="simple_white")
show(fig)
""".strip()
        ),
        new_markdown_cell(
            "The full year is already aggregated. This is the chart behind finding 1."
        ),
        new_code_cell(
            """
full_hourly = pd.read_csv(AGG / "02_hourly_demand.csv")
fig = px.bar(
    full_hourly,
    x="hour",
    y="trips",
    title="2024: pickups by hour",
    labels={"hour": "Hour", "trips": "Trips"},
)
fig.update_layout(template="simple_white")
peak = full_hourly.loc[full_hourly["trips"].idxmax()]
print(f"Peak hour {int(peak['hour'])}: {int(peak['trips']):,} trips ({peak['share']:.1%})")
show(fig)
""".strip()
        ),
        new_markdown_cell("## Where trips start"),
        new_code_cell(
            """
labeled = population.merge(
    zones,
    left_on="PULocationID",
    right_on="LocationID",
    how="left",
)
top_zones = (
    labeled.groupby(["Borough", "Zone"], as_index=False)
    .size()
    .rename(columns={"size": "pickups"})
    .sort_values("pickups", ascending=False)
    .head(10)
)
fig = px.bar(
    top_zones.sort_values("pickups"),
    x="pickups",
    y="Zone",
    color="Borough",
    orientation="h",
    title="Sample: top pickup zones",
)
fig.update_layout(template="simple_white")
show(fig)
""".strip()
        ),
        new_code_cell(
            """
full_zones = pd.read_csv(AGG / "03_zone_rankings.csv")
top = full_zones.nsmallest(12, "city_rank").sort_values("pickups")
fig = px.bar(
    top,
    x="pickups",
    y="zone",
    color="borough",
    orientation="h",
    title="2024: top pickup zones",
)
fig.update_layout(template="simple_white")
leader = full_zones.loc[full_zones["city_rank"].idxmin()]
print(f"{leader['zone']} ({leader['borough']}): {int(leader['pickups']):,} pickups")
show(fig)
""".strip()
        ),
        new_markdown_cell(
            "## Speed\n\n"
            "Miles per hour from distance and duration. The full-year query drops "
            "speeds outside 0.5–80 mph before taking the median."
        ),
        new_code_cell(
            """
moving = population[
    population["duration_sec"].gt(0) & population["trip_distance"].gt(0)
].copy()
moving["speed_mph"] = moving["trip_distance"] / (moving["duration_sec"] / 3600)
moving = moving[moving["speed_mph"].between(0.5, 80)].copy()
moving["hour"] = moving["pickup"].dt.hour
moving = moving.merge(
    zones[["LocationID", "Borough"]],
    left_on="PULocationID",
    right_on="LocationID",
    how="left",
)
speed = moving.groupby(["hour", "Borough"], as_index=False)["speed_mph"].median()
keep = ["Manhattan", "Brooklyn", "Queens", "Bronx"]
fig = px.line(
    speed[speed["Borough"].isin(keep)],
    x="hour",
    y="speed_mph",
    color="Borough",
    title="Sample: median speed by hour",
    labels={"speed_mph": "Median mph", "hour": "Hour"},
)
fig.update_layout(template="simple_white")
show(fig)
""".strip()
        ),
        new_code_cell(
            """
full_speed = pd.read_csv(AGG / "06_speed_by_hour_borough.csv")
boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx"]
fig = px.line(
    full_speed[full_speed["borough"].isin(boroughs)],
    x="hour",
    y="median_speed_mph",
    color="borough",
    title="2024: median speed by hour",
    labels={"median_speed_mph": "Median mph", "hour": "Hour"},
)
fig.update_layout(template="simple_white")
stable = full_speed[full_speed["trips"] >= 1000]
slow = stable.loc[stable["median_speed_mph"].idxmin()]
print(
    f"Slowest stable cell: {slow['borough']} hour {int(slow['hour'])}, "
    f"{slow['median_speed_mph']:.1f} mph"
)
show(fig)
""".strip()
        ),
    ]
    return _nb(cells)


def fare_notebook() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            "# Tips, airports, and data quality\n\n"
            "Pandas builds tip percent, an airport slice, and anomaly flags on the "
            "10k sample. The full-year bars come from the DuckDB extracts in `data/agg/`."
        ),
        new_code_cell(SETUP),
        new_code_cell(LOAD),
        new_code_cell(POPULATION),
        new_markdown_cell(
            "## Tip percent by payment type\n\n"
            "Tip percent is the tip divided by the pre-tip bill, "
            "`tip_amount / (total_amount - tip_amount)`. "
            "Payment type 1 is credit card and 2 is cash."
        ),
        new_code_cell(
            """
names = {0: "Not reported", 1: "Credit card", 2: "Cash", 3: "No charge", 4: "Dispute"}
tipped = population[
    population["payment_type"].isin([0, 1, 2, 3, 4])
    & population["tip_amount"].ge(0)
    & population["total_amount"].gt(population["tip_amount"])
].copy()
tipped["tip_pct"] = tipped["tip_amount"] / (tipped["total_amount"] - tipped["tip_amount"])
tipped["payment_name"] = tipped["payment_type"].map(names)
summary = tipped.groupby("payment_name", as_index=False).agg(
    trips=("tip_pct", "size"),
    median_tip_pct=("tip_pct", "median"),
    pct_with_tip=("tip_amount", lambda s: (s > 0).mean()),
)
fig = px.bar(
    summary,
    x="payment_name",
    y="median_tip_pct",
    title="Sample: median tip share of the pre-tip bill",
    labels={"median_tip_pct": "Median tip share", "payment_name": "Payment"},
)
fig.update_layout(template="simple_white")
show(fig)
summary
""".strip()
        ),
        new_code_cell(
            """
full_tips = pd.read_csv(AGG / "04_tip_by_payment.csv")
fig = px.bar(
    full_tips,
    x="payment_name",
    y="median_tip_pct",
    title="2024: median tip share of the pre-tip bill",
    labels={"median_tip_pct": "Median tip share", "payment_name": "Payment"},
)
fig.update_layout(template="simple_white")
card = full_tips.loc[full_tips["payment_type"] == 1].iloc[0]
cash = full_tips.loc[full_tips["payment_type"] == 2].iloc[0]
print(
    f"Card median tip {card['median_tip_pct']:.0%}; "
    f"cash median tip {cash['median_tip_pct']:.0%}"
)
show(fig)
""".strip()
        ),
        new_markdown_cell(
            "## Airport products\n\n"
            "JFK is zone 132, LaGuardia is 138, Newark is 1. Rate code 2 is the JFK flat fare."
        ),
        new_code_cell(
            """
airports = {1: "EWR", 132: "JFK", 138: "LGA"}
airport_trips = population[
    population["PULocationID"].isin(airports) | population["DOLocationID"].isin(airports)
].copy()
airport_trips["airport"] = airport_trips["PULocationID"].map(airports)
airport_trips["airport"] = airport_trips["airport"].fillna(
    airport_trips["DOLocationID"].map(airports)
)
airport_trips["product"] = airport_trips["RatecodeID"].map(
    {1: "Standard", 2: "JFK flat", 3: "Newark"}
).fillna("Other")
by_product = (
    airport_trips.groupby(["airport", "product"], as_index=False)
    .agg(trips=("fare_amount", "size"), median_fare=("fare_amount", "median"))
    .sort_values("trips", ascending=False)
)
fig = px.bar(
    by_product,
    x="product",
    y="median_fare",
    color="airport",
    barmode="group",
    title="Sample: median fare by airport product",
    labels={"median_fare": "Median fare", "product": "Product"},
)
fig.update_layout(template="simple_white")
show(fig)
by_product.head(8)
""".strip()
        ),
        new_code_cell(
            """
full_airport = pd.read_csv(AGG / "05_airport_economics.csv")
focus = full_airport[
    (
        (full_airport["airport"] == "JFK")
        & (full_airport["product"] == "JFK flat")
        & (full_airport["direction"] == "to Manhattan")
    )
    | (
        (full_airport["airport"] == "LGA")
        & (full_airport["product"] == "Standard")
        & (full_airport["direction"] == "to Manhattan")
    )
    | (
        (full_airport["airport"] == "EWR")
        & (full_airport["product"] == "Newark")
        & (full_airport["direction"] == "from Manhattan")
    )
].copy()
focus["label"] = focus["airport"] + " " + focus["product"]
fig = px.bar(
    focus,
    x="label",
    y=["median_fare", "median_total"],
    barmode="group",
    title="2024: fare and all-in total on the main airport products",
    labels={"value": "Dollars", "label": "Product", "variable": ""},
)
fig.update_layout(template="simple_white")
show(fig)
focus[["airport", "product", "direction", "trips", "median_fare", "median_total", "median_miles"]]
""".strip()
        ),
        new_markdown_cell(
            "## Anomaly flags\n\n"
            "The same rules as `sql/07_anomaly_rules.sql`, expressed as pandas masks "
            "on the sample. A row can trip more than one."
        ),
        new_code_cell(
            """
rules = pd.DataFrame(
    {
        "nonpositive_distance": trips["trip_distance"].le(0),
        "nonpositive_fare": trips["fare_amount"].le(0),
        "negative_total": trips["total_amount"].lt(0),
        "time_inverted": trips["dropoff"].le(trips["pickup"]),
        "duration_over_3h": trips["duration_sec"].gt(10800),
        "speed_over_80": (trips["trip_distance"] / (trips["duration_sec"] / 3600)).gt(80),
        "tip_exceeds_fare": trips["fare_amount"].gt(0)
        & trips["tip_amount"].gt(trips["fare_amount"]),
    }
)
rates = rules.mean().rename_axis("rule").reset_index(name="flag_rate")
rates = rates.sort_values("flag_rate")
fig = px.bar(
    rates,
    x="flag_rate",
    y="rule",
    orientation="h",
    title="Sample: share of rows flagged",
    labels={"flag_rate": "Share of sample rows", "rule": "Rule"},
)
fig.update_layout(template="simple_white")
show(fig)
rates
""".strip()
        ),
        new_markdown_cell("## Completeness on the full file"),
        new_code_cell(
            """
quality = pd.read_csv(AGG / "01_data_quality.csv").sort_values("flag_rate")
fig = px.bar(
    quality,
    x="flag_rate",
    y="check_name",
    orientation="h",
    title="2024: data-quality checks",
    labels={"flag_rate": "Share of published rows", "check_name": "Check"},
)
fig.update_layout(template="simple_white", yaxis={"categoryorder": "total ascending"})
vendor = quality.loc[quality["check_name"] == "vendor_fields_missing"].iloc[0]
excluded = quality.loc[quality["check_name"] == "excluded_from_analysis"].iloc[0]
print(
    f"Vendor feed {int(vendor['flagged']):,} rows ({vendor['flag_rate']:.1%}); "
    f"excluded from KPIs {int(excluded['flagged']):,} ({excluded['flag_rate']:.1%})"
)
show(fig)
""".strip()
        ),
    ]
    return _nb(cells)


def execute(path, notebook: nbformat.NotebookNode) -> None:
    client = NotebookClient(
        notebook,
        kernel_name="taxi-insights",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    path.write_text(nbformat.writes(notebook), encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    notebook_dir = ROOT / "notebooks"
    notebook_dir.mkdir(parents=True, exist_ok=True)
    execute(notebook_dir / "01_demand_zones_speed.ipynb", demand_notebook())
    execute(notebook_dir / "02_tips_airports_quality.ipynb", fare_notebook())


if __name__ == "__main__":
    main()
