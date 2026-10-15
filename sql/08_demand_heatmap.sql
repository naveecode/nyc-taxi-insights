-- Pickup demand by day of week and hour for in-policy 2024 trips.
-- DuckDB EXTRACT(dow) is Sunday = 0 through Saturday = 6.
-- Grain: day of week x hour.
-- Windows: share of that weekday, and the hour's rank within the weekday.

WITH cells AS (
    SELECT
        pickup_dow,
        hour,
        COUNT(*) AS trips
    FROM population
    GROUP BY pickup_dow, hour
)
SELECT
    pickup_dow,
    hour,
    trips,
    trips * 1.0 / SUM(trips) OVER (PARTITION BY pickup_dow) AS share_of_dow,
    RANK() OVER (
        PARTITION BY pickup_dow
        ORDER BY trips DESC, hour
    ) AS hour_rank_in_dow
FROM cells
ORDER BY pickup_dow, hour;
