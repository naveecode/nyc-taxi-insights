-- Implausible-value rules applied to every published row.
-- A row can trip more than one rule. flag_rate is the share of published
-- rows. share_of_flags divides each rule by the sum of flags, so it is not
-- a share of trips.
-- Grain: one row per rule.
-- Window: severity rank and share of all flags.

WITH scored AS (
    SELECT
        NOT pickup_in_2024 AS pickup_outside_2024,
        tpep_dropoff_datetime <= tpep_pickup_datetime AS time_inverted,
        trip_distance <= 0 AS nonpositive_distance,
        fare_amount <= 0 AS nonpositive_fare,
        total_amount < 0 AS negative_total,
        duration_sec > 10800 AS duration_over_3h,
        speed_mph > 80 AS speed_over_80,
        fare_amount > 0 AND tip_amount > fare_amount AS tip_exceeds_fare,
        passenger_count IS NOT NULL
            AND (passenger_count < 1 OR passenger_count > 6) AS passenger_out_of_range,
        RatecodeID = 2
            AND NOT (
                (PULocationID = 132 AND do_borough = 'Manhattan')
                OR (DOLocationID = 132 AND pu_borough = 'Manhattan')
            ) AS jfk_flat_off_manhattan
    FROM trips_enriched
),
rules AS (
    SELECT
        'nonpositive_distance' AS rule,
        'Distance is zero or negative' AS description,
        COUNT(*) FILTER (WHERE nonpositive_distance) AS flagged,
        COUNT(*) AS total_rows
    FROM scored
    UNION ALL
    SELECT
        'nonpositive_fare',
        'Fare is zero or negative',
        COUNT(*) FILTER (WHERE nonpositive_fare),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'negative_total',
        'Total amount is negative',
        COUNT(*) FILTER (WHERE negative_total),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'time_inverted',
        'Dropoff is at or before pickup',
        COUNT(*) FILTER (WHERE time_inverted),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'duration_over_3h',
        'Duration is longer than three hours',
        COUNT(*) FILTER (WHERE duration_over_3h),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'speed_over_80',
        'Implied speed is over 80 mph',
        COUNT(*) FILTER (WHERE speed_over_80),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'tip_exceeds_fare',
        'Tip is larger than the fare on a positive fare',
        COUNT(*) FILTER (WHERE tip_exceeds_fare),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'passenger_out_of_range',
        'Passenger count is outside 1-6',
        COUNT(*) FILTER (WHERE passenger_out_of_range),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'pickup_outside_2024',
        'Pickup timestamp is outside calendar year 2024',
        COUNT(*) FILTER (WHERE pickup_outside_2024),
        COUNT(*)
    FROM scored
    UNION ALL
    SELECT
        'jfk_flat_off_manhattan',
        'JFK flat fare (RatecodeID 2) is not a JFK-Manhattan trip',
        COUNT(*) FILTER (WHERE jfk_flat_off_manhattan),
        COUNT(*)
    FROM scored
)
SELECT
    rule,
    description,
    flagged,
    total_rows,
    flagged * 1.0 / total_rows AS flag_rate,
    RANK() OVER (ORDER BY flagged DESC, rule) AS severity_rank,
    flagged * 1.0 / NULLIF(SUM(flagged) OVER (), 0) AS share_of_flags
FROM rules
ORDER BY severity_rank, rule;
