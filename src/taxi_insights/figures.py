"""Plotly charts shared by the static dashboard and the insight figures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from taxi_insights.format import hour_label
from taxi_insights.paths import DOW_SHORT, FIGURE_DIR, MONTH_NAMES

INK = "#1a1814"
MUTED = "#5c564c"
TEAL = "#1e4d5c"
AMBER = "#d4920a"
ROSE = "#8d3b3b"
GRID = "#eadfcd"
PAPER = "rgba(0,0,0,0)"

BOROUGH_COLORS = {
    "Manhattan": "#1e4d5c",
    "Brooklyn": "#d4920a",
    "Queens": "#3d7a8c",
    "Bronx": "#8d3b3b",
    "Staten Island": "#6b4c7a",
    "EWR": "#8a8175",
}

QUALITY_LABELS = {
    "missing_passenger_count": "Null passenger count",
    "missing_rate_code": "Null rate code",
    "payment_not_reported": "Payment not reported",
    "vendor_fields_missing": "Payment 0 with null passenger and rate",
    "unknown_pickup_zone": "Unknown pickup zone",
    "missing_congestion_surcharge": "Null congestion surcharge",
    "missing_airport_fee": "Null airport fee",
    "pickup_outside_2024": "Pickup outside 2024",
    "excluded_from_analysis": "Excluded from KPI population",
}

AIRPORT_SLICES = (
    ("JFK", "JFK flat", "to Manhattan", "JFK flat → Manhattan"),
    ("JFK", "JFK flat", "from Manhattan", "JFK flat ← Manhattan"),
    ("JFK", "Standard", "to Manhattan", "JFK meter → Manhattan"),
    ("JFK", "JFK flat", "to other", "JFK flat → other"),
    ("LGA", "Standard", "to Manhattan", "LGA meter → Manhattan"),
    ("EWR", "Newark", "from Manhattan", "EWR Newark ← Manhattan"),
)


def _theme(fig: go.Figure, height: int = 460) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 48, "r": 24, "t": 48, "b": 48},
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font={"family": "Source Sans 3, Arial, sans-serif", "color": INK, "size": 14},
        title={"font": {"family": "Fraunces, Georgia, serif", "size": 20, "color": INK}},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0,
            "font": {"size": 13},
        },
        hoverlabel={"font_size": 13, "font_family": "Source Sans 3, Arial, sans-serif"},
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=GRID,
        tickfont={"color": MUTED},
        title_font={"color": MUTED, "size": 13},
    )
    fig.update_yaxes(
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickfont={"color": MUTED},
        title_font={"color": MUTED, "size": 13},
    )
    return fig


def hourly_figure(frame: pd.DataFrame) -> go.Figure:
    data = frame.sort_values("hour")
    peak = int(data.loc[data["trips"].idxmax(), "hour"])
    colors = [AMBER if int(hour) == peak else TEAL for hour in data["hour"]]
    fig = go.Figure(
        go.Bar(
            x=data["hour"],
            y=data["trips"],
            marker_color=colors,
            hovertemplate="Hour %{x}<br>%{y:,.0f} trips<extra></extra>",
        )
    )
    peak_trips = int(data.loc[data["hour"] == peak, "trips"].iloc[0])
    fig.add_annotation(
        x=peak,
        y=peak_trips,
        text=hour_label(peak),
        showarrow=True,
        arrowhead=2,
        arrowcolor=AMBER,
        ax=30,
        ay=-40,
        font={"color": INK, "size": 14},
    )
    fig.update_layout(title="Pickups by hour of day", yaxis_title="Trips", xaxis_title="Hour")
    fig.update_xaxes(dtick=1)
    return _theme(fig)


def heatmap_figure(frame: pd.DataFrame) -> go.Figure:
    order = [1, 2, 3, 4, 5, 6, 0]
    pivot = (
        frame.pivot(index="pickup_dow", columns="hour", values="trips")
        .reindex(order)
        .reindex(columns=list(range(24)))
    )
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=list(range(24)),
            y=[DOW_SHORT[day] for day in order],
            colorscale=[[0, "#f4f0e6"], [0.45, "#7f9eaa"], [1, "#1e4d5c"]],
            hovertemplate="%{y} %{x}:00<br>%{z:,.0f} trips<extra></extra>",
            colorbar={"title": "Trips", "tickfont": {"color": MUTED}},
        )
    )
    fig.update_layout(title="Demand by weekday and hour")
    fig.update_xaxes(title="Hour", dtick=1)
    fig.update_yaxes(title="")
    return _theme(fig, height=420)


def monthly_figure(frame: pd.DataFrame) -> go.Figure:
    data = frame.sort_values("pickup_month")
    leader = int(data.loc[data["trips_per_day"].idxmax(), "pickup_month"])
    colors = [AMBER if int(month) == leader else TEAL for month in data["pickup_month"]]
    fig = go.Figure(
        go.Bar(
            x=[MONTH_NAMES[int(month) - 1] for month in data["pickup_month"]],
            y=data["trips_per_day"],
            marker_color=colors,
            customdata=data["trips"],
            hovertemplate=(
                "%{x}<br>%{y:,.0f} trips per day<br>%{customdata:,.0f} trips<extra></extra>"
            ),
        )
    )
    fig.update_layout(title="Trips per day by month", yaxis_title="Trips per active day")
    return _theme(fig, height=420)


def zone_figure(frame: pd.DataFrame) -> go.Figure:
    data = frame.nsmallest(12, "city_rank").sort_values("pickups")
    fig = go.Figure(
        go.Bar(
            x=data["pickups"],
            y=[
                f"{zone}  ·  {borough}"
                for zone, borough in zip(data["zone"], data["borough"], strict=True)
            ],
            orientation="h",
            marker_color=[BOROUGH_COLORS.get(str(borough), TEAL) for borough in data["borough"]],
            hovertemplate="%{y}<br>%{x:,.0f} pickups<extra></extra>",
        )
    )
    fig.update_layout(title="Top pickup zones", xaxis_title="Pickups", yaxis_title="")
    fig.update_layout(margin={"l": 16, "r": 24, "t": 48, "b": 48})
    return _theme(fig, height=520)


def tip_figure(frame: pd.DataFrame) -> go.Figure:
    order = ["Credit card", "Cash", "Not reported", "No charge", "Dispute", "Unknown", "Other"]
    data = frame.copy()
    data["sort"] = data["payment_name"].map({name: index for index, name in enumerate(order)})
    data = data.sort_values(["sort", "payment_type"])
    fig = go.Figure(
        go.Bar(
            x=data["payment_name"],
            y=data["median_tip_pct"] * 100,
            marker_color=[
                AMBER if name == "Credit card" else TEAL for name in data["payment_name"]
            ],
            customdata=data["pct_with_tip"] * 100,
            hovertemplate=(
                "%{x}<br>median tip %{y:.1f}% of the pre-tip bill"
                "<br>%{customdata:.1f}% of trips have a tip<extra></extra>"
            ),
        )
    )
    fig.update_layout(title="Median tip as a share of the pre-tip bill", yaxis_title="Median tip %")
    return _theme(fig, height=420)


def airport_figure(frame: pd.DataFrame) -> go.Figure:
    rows = []
    for airport, product, direction, label in AIRPORT_SLICES:
        hit = frame[
            (frame["airport"] == airport)
            & (frame["product"] == product)
            & (frame["direction"] == direction)
        ]
        if len(hit) == 1:
            rows.append(hit.assign(label=label))
    data = pd.concat(rows, ignore_index=True)
    fig = go.Figure()
    fig.add_bar(
        name="Median fare",
        x=data["label"],
        y=data["median_fare"],
        marker_color=TEAL,
        hovertemplate="%{x}<br>fare %{y:.2f}<extra></extra>",
    )
    fig.add_bar(
        name="Median total",
        x=data["label"],
        y=data["median_total"],
        marker_color=AMBER,
        hovertemplate="%{x}<br>total %{y:.2f}<extra></extra>",
    )
    fig.update_layout(
        barmode="group",
        title="Airport fare and all-in total",
        yaxis_title="Dollars",
    )
    return _theme(fig, height=460)


def speed_figure(frame: pd.DataFrame) -> go.Figure:
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "EWR"]
    fig = go.Figure()
    for borough in boroughs:
        data = frame[frame["borough"] == borough].sort_values("hour")
        if data.empty:
            continue
        fig.add_scatter(
            name=borough,
            x=data["hour"],
            y=data["median_speed_mph"],
            mode="lines",
            line={"color": BOROUGH_COLORS[borough], "width": 2.4},
            hovertemplate=f"{borough} %{{x}}:00<br>%{{y:.1f}} mph<extra></extra>",
        )
    fig.update_layout(
        title="Median speed by pickup hour",
        yaxis_title="Miles per hour",
        xaxis_title="Hour",
    )
    fig.update_xaxes(dtick=1)
    return _theme(fig, height=480)


def quality_figure(frame: pd.DataFrame) -> go.Figure:
    data = frame.sort_values("flag_rate")
    labels = [QUALITY_LABELS.get(name, name) for name in data["check_name"]]
    fig = go.Figure(
        go.Bar(
            x=data["flag_rate"] * 100,
            y=labels,
            orientation="h",
            marker_color=[
                ROSE if name == "excluded_from_analysis" else TEAL for name in data["check_name"]
            ],
            hovertemplate="%{y}<br>%{x:.2f}% of published rows<extra></extra>",
        )
    )
    fig.update_layout(title="Data-quality checks", xaxis_title="Percent of published rows")
    return _theme(fig, height=480)


def anomaly_figure(frame: pd.DataFrame) -> go.Figure:
    data = frame.sort_values("flag_rate")
    fig = go.Figure(
        go.Bar(
            x=data["flag_rate"] * 100,
            y=data["description"],
            orientation="h",
            marker_color=TEAL,
            customdata=data["flagged"],
            hovertemplate="%{y}<br>%{x:.2f}% of rows<br>%{customdata:,.0f} rows<extra></extra>",
        )
    )
    fig.update_layout(title="Anomaly rules", xaxis_title="Percent of published rows")
    return _theme(fig, height=480)


FIGURES = {
    "hourly_demand": hourly_figure,
    "demand_heatmap": heatmap_figure,
    "monthly_volume": monthly_figure,
    "zone_rankings": zone_figure,
    "tip_by_payment": tip_figure,
    "airport_economics": airport_figure,
    "speed_by_hour": speed_figure,
    "data_quality": quality_figure,
    "anomaly_rules": anomaly_figure,
}

FRAME_KEYS = {
    "hourly_demand": "02_hourly_demand",
    "demand_heatmap": "08_demand_heatmap",
    "monthly_volume": "09_monthly_volume",
    "zone_rankings": "03_zone_rankings",
    "tip_by_payment": "04_tip_by_payment",
    "airport_economics": "05_airport_economics",
    "speed_by_hour": "06_speed_by_hour_borough",
    "data_quality": "01_data_quality",
    "anomaly_rules": "07_anomaly_rules",
}


def build_figures(frames: dict[str, pd.DataFrame]) -> dict[str, go.Figure]:
    return {key: builder(frames[FRAME_KEYS[key]]) for key, builder in FIGURES.items()}


def write_figures(figures: dict[str, go.Figure], directory: Path = FIGURE_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for key, fig in figures.items():
        destination = directory / f"{key}.png"
        fig.write_image(destination, width=1200, height=700, scale=2)
        print(f"wrote {destination}")


def chart_title(key: str) -> str:
    """Short caption used as image alt text. The live title sits on the figure."""
    titles = {
        "hourly_demand": "Pickups by hour of day",
        "demand_heatmap": "Demand by weekday and hour",
        "monthly_volume": "Trips per day by month",
        "zone_rankings": "Top pickup zones",
        "tip_by_payment": "Median tip percent by payment type",
        "airport_economics": "Airport median fare and total",
        "speed_by_hour": "Median speed by hour and borough",
        "data_quality": "Data-quality check rates",
        "anomaly_rules": "Anomaly rule rates",
    }
    return titles[key]


def main() -> None:
    from taxi_insights.narrative import load_frames

    write_figures(build_figures(load_frames()))


if __name__ == "__main__":
    main()
