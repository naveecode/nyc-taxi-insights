-- Pickup demand by hour of day for in-policy 2024 trips.
-- Grain: one row per clock hour (0-23).
-- Windows: share of the year, running share, hour-to-hour change,
-- demand rank, and a 3-hour centered average.

WITH hourly AS (
    SELECT
        hour,
        COUNT(*) AS trips,
        COUNT(DISTINCT pickup_date) AS active_days
    FROM population
    GROUP BY hour
)
SELECT
    hour,
    trips,
    active_days,
    trips * 1.0 / active_days AS avg_trips_per_active_day,
    trips * 1.0 / SUM(trips) OVER () AS share,
    SUM(trips) OVER (
        ORDER BY hour
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) * 1.0 / SUM(trips) OVER () AS cumulative_share,
    trips - LAG(trips) OVER (ORDER BY hour) AS trip_delta,
    RANK() OVER (ORDER BY trips DESC, hour) AS demand_rank,
    AVG(trips) OVER (
        ORDER BY hour
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) AS smooth_3h
FROM hourly
ORDER BY hour;
