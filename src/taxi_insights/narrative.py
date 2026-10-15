"""Findings computed from the aggregate extracts. Numbers are read, not typed."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from taxi_insights.format import commas, hour_label, miles, money, pct, ratio
from taxi_insights.paths import AGG_DIR, DOW_NAMES, HEADLINES, MONTH_NAMES, QUERY_FILES, query_stem

DASHBOARD_URL = "https://naveecode.github.io/nyc-taxi-insights/"


@dataclass(frozen=True)
class Finding:
    slug: str
    title: str
    question: str
    queries: tuple[str, ...]
    charts: tuple[str, ...]
    headline: str
    detail: str
    recommendation: str


def load_frames() -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for filename in QUERY_FILES:
        stem = query_stem(filename)
        frames[stem] = pd.read_csv(AGG_DIR / f"{stem}.csv")
    return frames


def _one(frame: pd.DataFrame, **filters: object) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in filters.items():
        mask &= frame[column] == value
    hit = frame.loc[mask]
    if len(hit) != 1:
        raise KeyError(f"{filters} matched {len(hit)} rows")
    return hit.iloc[0]


def _check(frame: pd.DataFrame, name: str) -> pd.Series:
    return _one(frame, check_name=name)


def _rule(frame: pd.DataFrame, name: str) -> pd.Series:
    return _one(frame, rule=name)


def build_headlines(frames: dict[str, pd.DataFrame]) -> dict[str, object]:
    hourly = frames["02_hourly_demand"]
    zones = frames["03_zone_rankings"]
    tips = frames["04_tip_by_payment"]
    airport = frames["05_airport_economics"]
    speed = frames["06_speed_by_hour_borough"]
    quality = frames["01_data_quality"]
    anomalies = frames["07_anomaly_rules"]
    monthly = frames["09_monthly_volume"]

    peak = hourly.loc[hourly["trips"].idxmax()]
    top = zones.loc[zones["city_rank"].idxmin()]
    top10 = zones.loc[zones["city_rank"] == 10].iloc[0]
    busy = monthly.loc[monthly["daily_rate_rank"].idxmin()]
    quiet = monthly.loc[monthly["daily_rate_rank"].idxmax()]
    card = _one(tips, payment_type=1)
    cash = _one(tips, payment_type=2)
    flat = _one(airport, airport="JFK", product="JFK flat", direction="to Manhattan")
    stable = speed[speed["trips"] >= 1000]
    slow = stable.loc[stable["median_speed_mph"].idxmin()]
    excluded = _check(quality, "excluded_from_analysis")
    vendor = _check(quality, "vendor_fields_missing")
    top_rule = anomalies.loc[anomalies["severity_rank"].idxmin()]

    return {
        "population_trips": int(hourly["trips"].sum()),
        "published_rows": int(excluded["total_rows"]),
        "excluded_rows": int(excluded["flagged"]),
        "excluded_rate": float(excluded["flag_rate"]),
        "peak_hour": int(peak["hour"]),
        "peak_hour_label": hour_label(int(peak["hour"])),
        "peak_share": float(peak["share"]),
        "top_zone": str(top["zone"]),
        "top_zone_borough": str(top["borough"]),
        "top_zone_share": float(top["city_share"]),
        "top10_share": float(top10["cumulative_share"]),
        "busiest_month": int(busy["pickup_month"]),
        "busiest_month_name": MONTH_NAMES[int(busy["pickup_month"]) - 1],
        "quietest_month_name": MONTH_NAMES[int(quiet["pickup_month"]) - 1],
        "card_median_tip_pct": float(card["median_tip_pct"]),
        "cash_median_tip_pct": float(cash["median_tip_pct"]),
        "jfk_flat_fare": float(flat["median_fare"]),
        "jfk_flat_total": float(flat["median_total"]),
        "jfk_flat_miles": float(flat["median_miles"]),
        "slowest_borough": str(slow["borough"]),
        "slowest_hour": int(slow["hour"]),
        "slowest_hour_label": hour_label(int(slow["hour"])),
        "slowest_mph": float(slow["median_speed_mph"]),
        "top_quality_check": "vendor_fields_missing",
        "vendor_rows": int(vendor["flagged"]),
        "top_anomaly_rule": str(top_rule["rule"]),
        "dashboard_url": DASHBOARD_URL,
    }


def save_headlines(headlines: dict[str, object]) -> None:
    HEADLINES.write_text(json.dumps(headlines, indent=2) + "\n", encoding="utf-8")


def _demand(frames: dict[str, pd.DataFrame]) -> Finding:
    hourly = frames["02_hourly_demand"]
    heat = frames["08_demand_heatmap"]
    peak = hourly.loc[hourly["trips"].idxmax()]
    quiet = hourly.loc[hourly["trips"].idxmin()]
    top3 = hourly.nsmallest(3, "demand_rank")
    top3_share = float(top3["share"].sum())
    top3_labels = ", ".join(hour_label(int(hour)) for hour in top3.sort_values("hour")["hour"])
    peak_hour = int(peak["hour"])
    morning = hourly.loc[hourly["hour"] == 8].iloc[0]
    peaks_by_hour: dict[int, list[str]] = {}
    for dow, name in enumerate(DOW_NAMES):
        day = heat[heat["pickup_dow"] == dow]
        if day.empty:
            continue
        day_peak = int(day.loc[day["trips"].idxmax(), "hour"])
        peaks_by_hour.setdefault(day_peak, []).append(name)
    peak_label = hour_label(peak_hour)
    if len(peaks_by_hour) == 1:
        shape = f"Every day of the week peaks at {peak_label}"
        roster = (
            "Use one peak window for the whole week, and do not staff the overnight "
            "as if it were a second rush."
        )
    else:
        parts = [
            f"{', '.join(names)} peak at {hour_label(hour)}"
            for hour, names in sorted(peaks_by_hour.items(), key=lambda item: -len(item[1]))
        ]
        shape = "; ".join(parts)
        if not shape.endswith("."):
            shape += "."
        majority_hour = max(peaks_by_hour, key=lambda hour: len(peaks_by_hour[hour]))
        exceptions = ", ".join(
            f"{', '.join(names)} toward {hour_label(hour)}"
            for hour, names in peaks_by_hour.items()
            if hour != majority_hour
        )
        roster = (
            f"Keep the {hour_label(majority_hour)} roster for "
            f"{', '.join(peaks_by_hour[majority_hour])}, and shift {exceptions}"
        )
        if not roster.endswith("."):
            roster += "."

    morning_clause = ""
    if peak_hour != 8:
        morning_clause = (
            f" That is {ratio(float(peak['trips']) / float(morning['trips']))} the 8 a.m. hour "
            f"({commas(morning['trips'])} trips)."
        )

    headline = (
        f"{peak_label} accounts for {pct(float(peak['share']))} of in-policy trips "
        f"({commas(peak['trips'])})."
    )
    detail = (
        f"Across {commas(hourly['trips'].sum())} in-policy trips, the busiest clock hour is "
        f"{peak_label}{morning_clause} The top three hours ({top3_labels}) are "
        f"{pct(top3_share)} of demand. The quietest hour is {hour_label(int(quiet['hour']))}, "
        f"with {commas(quiet['trips'])} trips ({pct(float(quiet['share']))}). {shape}"
    )
    recommendation = (
        f"Staff street hail and dispatch for {peak_label} {roster} "
        f"The quietest hour is only {pct(float(quiet['share']))} of the year, so a flat "
        "headcount across 24 hours overstaffs the night."
    )
    return Finding(
        slug="demand",
        title=f"Demand peaks at {peak_label}",
        question="When do yellow cabs actually get busy, and is that peak the same all week?",
        queries=("sql/02_hourly_demand.sql", "sql/08_demand_heatmap.sql"),
        charts=("hourly_demand", "demand_heatmap"),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _season(frames: dict[str, pd.DataFrame]) -> Finding:
    monthly = frames["09_monthly_volume"]
    busy = monthly.loc[monthly["daily_rate_rank"].idxmin()]
    quiet = monthly.loc[monthly["daily_rate_rank"].idxmax()]
    busy_name = MONTH_NAMES[int(busy["pickup_month"]) - 1]
    quiet_name = MONTH_NAMES[int(quiet["pickup_month"]) - 1]
    gap = float(busy["trips_per_day"]) / float(quiet["trips_per_day"])
    volume_leader = monthly.loc[monthly["volume_rank"].idxmin()]
    volume_name = MONTH_NAMES[int(volume_leader["pickup_month"]) - 1]
    if int(volume_leader["pickup_month"]) == int(busy["pickup_month"]):
        volume_note = f"{busy_name} also leads on total trips ({commas(busy['trips'])})."
    else:
        volume_note = (
            f"Total trips peak in {volume_name} ({commas(volume_leader['trips'])}), "
            f"which is not the same ranking as trips per day."
        )
    headline = (
        f"{busy_name} runs {commas(busy['trips_per_day'])} in-policy trips per day, "
        f"{ratio(gap)} {quiet_name}."
    )
    detail = (
        f"{busy_name} has {int(busy['active_days'])} active pickup days and "
        f"{commas(busy['trips'])} in-policy trips. {quiet_name} has "
        f"{int(quiet['active_days'])} active days and {commas(quiet['trips'])} trips, "
        f"or {commas(quiet['trips_per_day'])} per day. {volume_note} "
        "The per-day rate is the fair comparison: months do not have the same length, "
        "and 2024 is a leap year."
    )
    recommendation = (
        "Set the annual run rate from the full year, not from a single extract. "
        f"A plan sized to {quiet_name} covers "
        f"{pct(float(quiet['trips_per_day']) / float(busy['trips_per_day']))} "
        f"of {busy_name}'s daily volume. "
        "Compare months on trips per day before calling a change seasonal."
    )
    return Finding(
        slug="seasonality",
        title=f"{busy_name} is the busiest month per day",
        question="Which month is actually the busiest once month length is taken out?",
        queries=("sql/09_monthly_volume.sql",),
        charts=("monthly_volume",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _zones(frames: dict[str, pd.DataFrame]) -> Finding:
    zones = frames["03_zone_rankings"]
    top = zones.loc[zones["city_rank"].idxmin()]
    top10 = zones.loc[zones["city_rank"] == 10].iloc[0]
    second = zones.loc[zones["city_rank"] == 2].iloc[0]
    borough_pickups = zones.groupby("borough")["pickups"].sum()
    manhattan_share = float(borough_pickups["Manhattan"] / borough_pickups.sum())
    queens = zones[zones["borough"] == "Queens"]
    queens_airports = queens[queens["zone"].isin(["JFK Airport", "LaGuardia Airport"])]
    queens_airport_share = float(queens_airports["pickups"].sum() / queens["pickups"].sum())
    headline = (
        f"{top['zone']} ({top['borough']}) is {pct(float(top['city_share']))} of pickups, "
        f"and the top 10 zones are {pct(float(top10['cumulative_share']))}."
    )
    detail = (
        f"{top['zone']} produced {commas(top['pickups'])} in-policy pickups, "
        f"{pct(float(top['borough_share']))} of all {top['borough']} pickups. "
        f"Second is {second['zone']} in {second['borough']} "
        f"({commas(second['pickups'])} pickups, {pct(float(second['city_share']))} of the city, "
        f"{pct(float(second['borough_share']))} of {second['borough']}). "
        f"Manhattan is {pct(manhattan_share)} of all pickups. "
        f"The two airports are {pct(queens_airport_share)} of Queens pickups. "
        f"The running share in sql/03_zone_rankings.sql reaches "
        f"{pct(float(top10['cumulative_share']))} by city rank 10, out of {len(zones)} zones "
        "with a known borough."
    )
    recommendation = (
        f"Stage vehicles for {top['zone']} and the other nine zones inside that "
        f"{pct(float(top10['cumulative_share']))} share before spreading coverage evenly. "
        "Use borough rank from the same query when a zone is the main stand in its borough "
        "without cracking the citywide top 10."
    )
    return Finding(
        slug="zones",
        title=f"Pickups concentrate at {top['zone']}",
        question="How concentrated is pickup demand across taxi zones?",
        queries=("sql/03_zone_rankings.sql",),
        charts=("zone_rankings",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _tips(frames: dict[str, pd.DataFrame]) -> Finding:
    tips = frames["04_tip_by_payment"]
    card = _one(tips, payment_type=1)
    cash = _one(tips, payment_type=2)
    missing = _one(tips, payment_type=0)
    card_pct = pct(float(card["median_tip_pct"]))
    if float(cash["median_tip_pct"]) < 0.005 and float(cash["pct_with_tip"]) < 0.02:
        cash_claim = (
            f"Cash records a median tip of {money(float(cash['median_tip']))} and a tip on "
            f"{pct(float(cash['pct_with_tip']))} of trips. That is a recording gap, not a "
            "measurement of cash generosity."
        )
    else:
        cash_claim = (
            f"Cash records a median tip of {pct(float(cash['median_tip_pct']))} "
            f"({pct(float(cash['pct_with_tip']))} of cash trips have any tip)."
        )
    headline = (
        f"The median credit-card tip is {card_pct} of the pre-tip bill "
        f"({money(float(card['median_tip']))})."
    )
    detail = (
        f"Credit-card trips are {pct(float(card['trip_share']))} of the tip population "
        f"({commas(card['trips'])} trips). A tip is present on {pct(float(card['pct_with_tip']))} "
        f"of them, the median tip percent is {card_pct}, and the mean is "
        f"{pct(float(card['avg_tip_pct']))}. {cash_claim} Payment type 0 "
        f"({pct(float(missing['trip_share']))} of this population) has a median tip percent of "
        f"{pct(float(missing['median_tip_pct']))} and a tip on "
        f"{pct(float(missing['pct_with_tip']))} of trips, so it is not a stand-in for cash."
    )
    recommendation = (
        "Publish tip rate from credit-card trips only. Treat cash tip fields as unobserved. "
        "Keep payment type 0 out of both groups: the payment field itself was not reported, "
        "and pooling it with cash would mix a partial tip signal into a column that is "
        "otherwise empty."
    )
    return Finding(
        slug="tips",
        title=f"The median card tip is {card_pct}",
        question="What share of the bill do riders tip, and can cash trips be included?",
        queries=("sql/04_tip_by_payment.sql",),
        charts=("tip_by_payment",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _airports(frames: dict[str, pd.DataFrame]) -> Finding:
    airport = frames["05_airport_economics"]
    anomalies = frames["07_anomaly_rules"]
    flat = _one(airport, airport="JFK", product="JFK flat", direction="to Manhattan")
    flat_from = _one(airport, airport="JFK", product="JFK flat", direction="from Manhattan")
    meter = _one(airport, airport="JFK", product="Standard", direction="to Manhattan")
    off = _one(airport, airport="JFK", product="JFK flat", direction="to other")
    lga = _one(airport, airport="LGA", product="Standard", direction="to Manhattan")
    ewr = _one(airport, airport="EWR", product="Newark", direction="from Manhattan")
    off_rule = _rule(anomalies, "jfk_flat_off_manhattan")

    if float(meter["median_fare"]) > float(flat["median_fare"]):
        meter_sentence = (
            f"Metered JFK-to-Manhattan trips are uncommon next to the flat fare "
            f"({commas(meter['trips'])} versus {commas(flat['trips'])}) and cost more: "
            f"median fare {money(float(meter['median_fare']))} against "
            f"{money(float(flat['median_fare']))}."
        )
    else:
        meter_sentence = (
            f"Metered JFK-to-Manhattan trips ({commas(meter['trips'])}) have a median fare of "
            f"{money(float(meter['median_fare']))}, against "
            f"{money(float(flat['median_fare']))} on the flat fare "
            f"({commas(flat['trips'])} trips)."
        )

    headline = (
        f"JFK to Manhattan is a {money(float(flat['median_fare']))} median fare "
        f"({money(float(flat['median_total']))} all-in) over {miles(float(flat['median_miles']))}."
    )
    detail = (
        f"The flat-fare product to Manhattan covers {commas(flat['trips'])} in-policy trips. "
        f"Median distance is {miles(float(flat['median_miles']))}, median time is "
        f"{float(flat['median_minutes']):.0f} minutes, and median fare per mile is "
        f"{money(float(flat['median_fare_per_mile']))}. The return, Manhattan to JFK, is "
        f"{commas(flat_from['trips'])} trips at the same median fare of "
        f"{money(float(flat_from['median_fare']))} and an all-in median of "
        f"{money(float(flat_from['median_total']))}. {meter_sentence} "
        f"In-policy JFK flat trips that drop off outside Manhattan still show a median fare of "
        f"{money(float(off['median_fare']))} ({commas(off['trips'])} trips, median "
        f"{miles(float(off['median_miles']))}), and "
        f"{pct(float(off['pct_under_5_miles']))} of that slice is under 5 miles. "
        f"The anomaly rule counts {commas(off_rule['flagged'])} published rows where rate code 2 "
        "is not a JFK–Manhattan pair. "
        f"LaGuardia to Manhattan is metered: median fare {money(float(lga['median_fare']))}, "
        f"median total {money(float(lga['median_total']))}, median tolls "
        f"{money(float(lga['median_tolls']))}, median tip {money(float(lga['median_tip']))}, "
        f"over {miles(float(lga['median_miles']))}. "
        f"Newark from Manhattan, on the Newark rate, is the expensive product: median fare "
        f"{money(float(ewr['median_fare']))}, median total {money(float(ewr['median_total']))}, "
        f"{miles(float(ewr['median_miles']))}, {commas(ewr['trips'])} trips."
    )
    recommendation = (
        f"Quote the JFK–Manhattan flat fare as {money(float(flat['median_fare']))} on the meter "
        f"and about {money(float(flat['median_total']))} all-in, for a ride of about "
        f"{miles(float(flat['median_miles']))}. Audit rate code 2 when the other end is not "
        f"Manhattan: those trips still carry a {money(float(off['median_fare']))} median fare, "
        f"including a {pct(float(off['pct_under_5_miles']))} share under 5 miles. "
        f"For LaGuardia to Manhattan, quote the all-in median "
        f"({money(float(lga['median_total']))}), not the meter fare alone "
        f"({money(float(lga['median_fare']))})."
    )
    return Finding(
        slug="airports",
        title=f"The JFK flat fare to Manhattan is {money(float(flat['median_fare']))}",
        question="What does the JFK flat fare actually cost, and where is it being misapplied?",
        queries=("sql/05_airport_economics.sql", "sql/07_anomaly_rules.sql"),
        charts=("airport_economics",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _speed(frames: dict[str, pd.DataFrame]) -> Finding:
    speed = frames["06_speed_by_hour_borough"]
    stable = speed[speed["trips"] >= 1000]
    if stable.empty:
        raise RuntimeError("No borough-hour has 1,000 trips; speed ranking would be noise.")
    slow = stable.loc[stable["median_speed_mph"].idxmin()]
    fast = stable.loc[stable["median_speed_mph"].idxmax()]
    manhattan = stable[stable["borough"] == "Manhattan"]
    man_slow = manhattan.loc[manhattan["median_speed_mph"].idxmin()]
    man_fast = manhattan.loc[manhattan["median_speed_mph"].idxmax()]
    gap = float(fast["median_speed_mph"]) - float(slow["median_speed_mph"])
    headline = (
        f"{slow['borough']} at {hour_label(int(slow['hour']))} moves at "
        f"{float(slow['median_speed_mph']):.1f} mph "
        f"({commas(slow['trips'])} trips)."
    )
    detail = (
        f"Among borough-hours with at least 1,000 in-policy trips, the slowest median is "
        f"{slow['borough']} at {hour_label(int(slow['hour']))} "
        f"({float(slow['median_speed_mph']):.1f} mph) and the fastest is {fast['borough']} at "
        f"{hour_label(int(fast['hour']))} ({float(fast['median_speed_mph']):.1f} mph), "
        f"a {gap:.1f} mph gap. Inside Manhattan the median runs from "
        f"{float(man_fast['median_speed_mph']):.1f} mph at "
        f"{hour_label(int(man_fast['hour']))} to "
        f"{float(man_slow['median_speed_mph']):.1f} mph at "
        f"{hour_label(int(man_slow['hour']))} "
        "Speeds above 80 mph are excluded here and counted in the anomaly rules, so a few "
        "broken timestamps cannot set the median."
    )
    recommendation = (
        f"Pad scheduled pickups from the borough-hour median. A citywide average hides the "
        f"{gap:.1f} mph gap between {slow['borough']} at {hour_label(int(slow['hour']))} and "
        f"{fast['borough']} at {hour_label(int(fast['hour']))} For Manhattan appointments, "
        f"the slow window is {hour_label(int(man_slow['hour']))} "
        f"({float(man_slow['median_speed_mph']):.1f} mph), not the early morning "
        f"({hour_label(int(man_fast['hour']))}, {float(man_fast['median_speed_mph']):.1f} mph)."
    )
    return Finding(
        slug="speed",
        title=f"{slow['borough']} is slowest at {hour_label(int(slow['hour']))}",
        question="Where and when does a yellow cab actually slow down?",
        queries=("sql/06_speed_by_hour_borough.sql",),
        charts=("speed_by_hour",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _quality(frames: dict[str, pd.DataFrame]) -> Finding:
    quality = frames["01_data_quality"]
    excluded = _check(quality, "excluded_from_analysis")
    vendor = _check(quality, "vendor_fields_missing")
    payment = _check(quality, "payment_not_reported")
    passengers = _check(quality, "missing_passenger_count")
    rates = _check(quality, "missing_rate_code")
    congestion = _check(quality, "missing_congestion_surcharge")
    airport_fee = _check(quality, "missing_airport_fee")
    outside = _check(quality, "pickup_outside_2024")
    cluster_counts = [
        int(vendor["flagged"]),
        int(payment["flagged"]),
        int(passengers["flagged"]),
        int(rates["flagged"]),
        int(congestion["flagged"]),
        int(airport_fee["flagged"]),
    ]
    inside_lower_bound = max(int(vendor["flagged"]) - int(excluded["flagged"]), 0)
    if len(set(cluster_counts)) == 1:
        cluster = (
            f"Six checks flag the same {commas(vendor['flagged'])} rows "
            f"({pct(float(vendor['flag_rate']))}). The fields move together: payment_type 0, "
            "null passenger_count, null RatecodeID, null congestion surcharge, and null "
            "airport fee. The intersection of payment type 0 with the two null trip fields "
            "is that same count, so it is one feed rather than five separate problems."
        )
    else:
        cluster = (
            f"The vendor intersection (payment 0 with null passenger and rate code) is "
            f"{commas(vendor['flagged'])} rows ({pct(float(vendor['flag_rate']))}). "
            f"Null airport fee is {commas(airport_fee['flagged'])} and null congestion "
            f"surcharge is {commas(congestion['flagged'])}."
        )
    headline = (
        f"{commas(vendor['flagged'])} rows ({pct(float(vendor['flag_rate']))}) are one "
        f"incomplete vendor feed. Trip filters drop only {pct(float(excluded['flag_rate']))}."
    )
    detail = (
        f"The files contain {commas(excluded['total_rows'])} published rows. "
        f"{commas(int(excluded['total_rows']) - int(excluded['flagged']))} survive the "
        f"in-policy definition in sql/00_population.sql "
        f"({commas(excluded['flagged'])} excluded, {pct(float(excluded['flag_rate']))}). "
        f"{cluster} At least {commas(inside_lower_bound)} of those incomplete rows still pass "
        "the trip filters, because the feed is larger than the excluded set even if every "
        "excluded row belonged to it. "
        f"Pickups outside 2024 are rare: {commas(outside['flagged'])} rows."
    )
    recommendation = (
        "Split the payment_type 0 feed out before any passenger-count, rate-code, airport-fee, "
        "or congestion analysis. Those fields are missing together, not zero. Keep the rows in "
        "demand and zone counts when distance and duration pass the population filters, and "
        f"print the trip-filter exclusion ({pct(float(excluded['flag_rate']))}) next to every KPI."
    )
    return Finding(
        slug="quality",
        title=f"{pct(float(vendor['flag_rate']))} of rows are one incomplete vendor feed",
        question="How much of the published file is usable, and what is the main hole?",
        queries=("sql/01_data_quality.sql", "sql/00_population.sql"),
        charts=("data_quality",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def _anomalies(frames: dict[str, pd.DataFrame]) -> Finding:
    anomalies = frames["07_anomaly_rules"]
    top = anomalies.loc[anomalies["severity_rank"].idxmin()]
    distance = _rule(anomalies, "nonpositive_distance")
    fare = _rule(anomalies, "nonpositive_fare")
    speed = _rule(anomalies, "speed_over_80")
    off = _rule(anomalies, "jfk_flat_off_manhattan")
    headline = (
        f"{top['description']} flags {commas(top['flagged'])} rows "
        f"({pct(float(top['flag_rate']))} of the file)."
    )
    detail = (
        "The rules are applied to every published row, and a row can trip more than one. "
        f"Non-positive distance flags {commas(distance['flagged'])} "
        f"({pct(float(distance['flag_rate']))}). Non-positive fare flags "
        f"{commas(fare['flagged'])} ({pct(float(fare['flag_rate']))}). "
        f"Implied speed over 80 mph flags {commas(speed['flagged'])} "
        f"({pct(float(speed['flag_rate']))}). "
        f"JFK flat fares that are not JFK–Manhattan trips flag {commas(off['flagged'])} "
        f"({pct(float(off['flag_rate']))}). "
        "The query's share-of-flags column divides by the sum of flags, so those shares "
        "are not a partition of trips and should not be added into a bad-row rate."
    )
    recommendation = (
        "Exclude these rules before any average of fare per mile, speed, or tip. "
        f"Start with {top['rule']}: it is the largest count. Do not add the flag rates "
        "together. Review the JFK flat-fare rule on its own before quoting the airport "
        f"product; it marks {commas(off['flagged'])} rows that are not the Manhattan flat fare."
    )
    return Finding(
        slug="anomalies",
        title=f"Largest anomaly: {top['description'][0].lower()}{top['description'][1:]}",
        question="Which implausible values will move a fare, speed, or tip average?",
        queries=("sql/07_anomaly_rules.sql",),
        charts=("anomaly_rules",),
        headline=headline,
        detail=detail,
        recommendation=recommendation,
    )


def build_findings(frames: dict[str, pd.DataFrame]) -> list[Finding]:
    return [
        _demand(frames),
        _season(frames),
        _zones(frames),
        _tips(frames),
        _airports(frames),
        _speed(frames),
        _quality(frames),
        _anomalies(frames),
    ]
