-- Pickup zone rankings for in-policy 2024 trips.
-- Grain: one row per pickup zone, excluding the TLC Unknown zone.
-- Windows: city rank, rank within borough, share of the city,
-- share of the borough, and cumulative city share.

WITH pickups AS (
    SELECT
        PULocationID AS location_id,
        pu_zone AS zone,
        pu_borough AS borough,
        COUNT(*) AS pickups
    FROM population
    WHERE pu_borough IS NOT NULL
      AND pu_borough <> 'Unknown'
    GROUP BY 1, 2, 3
)
SELECT
    location_id,
    zone,
    borough,
    pickups,
    RANK() OVER (ORDER BY pickups DESC, location_id) AS city_rank,
    RANK() OVER (
        PARTITION BY borough
        ORDER BY pickups DESC, location_id
    ) AS borough_rank,
    pickups * 1.0 / SUM(pickups) OVER () AS city_share,
    pickups * 1.0 / SUM(pickups) OVER (PARTITION BY borough) AS borough_share,
    SUM(pickups) OVER (
        ORDER BY pickups DESC, location_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) * 1.0 / SUM(pickups) OVER () AS cumulative_share
FROM pickups
ORDER BY city_rank;
