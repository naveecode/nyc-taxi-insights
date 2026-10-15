-- Monthly volume of in-policy 2024 trips.
-- trips_per_day uses the distinct pickup dates present in that month,
-- so a short month is not treated as a demand drop by itself.
-- Grain: one row per pickup month.
-- Windows: share of the year, month-over-month change, and ranks.

WITH monthly AS (
    SELECT
        pickup_month,
        COUNT(*) AS trips,
        COUNT(DISTINCT pickup_date) AS active_days
    FROM population
    GROUP BY pickup_month
),
rated AS (
    SELECT
        pickup_month,
        trips,
        active_days,
        trips * 1.0 / active_days AS trips_per_day
    FROM monthly
)
SELECT
    pickup_month,
    trips,
    active_days,
    trips_per_day,
    trips * 1.0 / SUM(trips) OVER () AS share,
    trips - LAG(trips) OVER (ORDER BY pickup_month) AS mom_change,
    (trips - LAG(trips) OVER (ORDER BY pickup_month)) * 1.0
        / LAG(trips) OVER (ORDER BY pickup_month) AS mom_pct,
    RANK() OVER (ORDER BY trips DESC, pickup_month) AS volume_rank,
    RANK() OVER (ORDER BY trips_per_day DESC, pickup_month) AS daily_rate_rank
FROM rated
ORDER BY pickup_month;
