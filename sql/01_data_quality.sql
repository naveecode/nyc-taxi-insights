-- Completeness of the published yellow-taxi files.
-- Grain: one row per quality check, scored against every published row.
-- Window functions rank checks by how many rows they flag and give each
-- check its share of all flags (flags overlap, so shares are not a partition).

WITH checks AS (
    SELECT
        'missing_passenger_count' AS check_name,
        'passenger_count is null' AS description,
        COUNT(*) FILTER (WHERE passenger_count IS NULL) AS flagged,
        COUNT(*) AS total_rows
    FROM trips_enriched
    UNION ALL
    SELECT
        'missing_rate_code',
        'RatecodeID is null',
        COUNT(*) FILTER (WHERE RatecodeID IS NULL),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'payment_not_reported',
        'payment_type is 0 or null',
        COUNT(*) FILTER (WHERE payment_type IS NULL OR payment_type = 0),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'vendor_fields_missing',
        'payment_type is 0 and passenger_count and RatecodeID are null',
        COUNT(*) FILTER (
            WHERE payment_type = 0
              AND passenger_count IS NULL
              AND RatecodeID IS NULL
        ),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'unknown_pickup_zone',
        'Pickup zone is missing or the TLC Unknown zone',
        COUNT(*) FILTER (WHERE pu_borough IS NULL OR pu_borough = 'Unknown'),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'missing_congestion_surcharge',
        'congestion_surcharge is null',
        COUNT(*) FILTER (WHERE congestion_surcharge IS NULL),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'missing_airport_fee',
        'Airport_fee is null',
        COUNT(*) FILTER (WHERE airport_fee IS NULL),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'pickup_outside_2024',
        'Pickup timestamp is outside calendar year 2024',
        COUNT(*) FILTER (WHERE NOT pickup_in_2024),
        COUNT(*)
    FROM trips_enriched
    UNION ALL
    SELECT
        'excluded_from_analysis',
        'Row fails the in-policy filters in sql/00_population.sql',
        (SELECT COUNT(*) FROM trips) - (SELECT COUNT(*) FROM population),
        (SELECT COUNT(*) FROM trips)
)
SELECT
    check_name,
    description,
    flagged,
    total_rows,
    flagged * 1.0 / total_rows AS flag_rate,
    RANK() OVER (ORDER BY flagged DESC, check_name) AS severity_rank,
    flagged * 1.0 / NULLIF(SUM(flagged) OVER (), 0) AS share_of_flags
FROM checks
ORDER BY severity_rank, check_name;
