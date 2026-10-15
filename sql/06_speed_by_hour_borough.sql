-- Median speed by pickup hour and pickup borough.
-- Speeds outside 0.5-80 mph are dropped here; they are counted as anomalies
-- in sql/07_anomaly_rules.sql instead of being allowed to pull the average.
-- Grain: borough x hour.
-- Windows: gap versus the borough's average hour, hour-to-hour change,
-- and the slowest hour among cells with at least 1,000 trips.

WITH speeds AS (
    SELECT
        pu_borough AS borough,
        hour,
        speed_mph
    FROM population
    WHERE speed_mph BETWEEN 0.5 AND 80
      AND pu_borough IN (
          'Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island', 'EWR'
      )
),
by_hour AS (
    SELECT
        borough,
        hour,
        COUNT(*) AS trips,
        MEDIAN(speed_mph) AS median_speed_mph,
        AVG(speed_mph) AS avg_speed_mph
    FROM speeds
    GROUP BY borough, hour
)
SELECT
    borough,
    hour,
    trips,
    median_speed_mph,
    avg_speed_mph,
    median_speed_mph
        - AVG(median_speed_mph) OVER (PARTITION BY borough) AS vs_borough_avg,
    median_speed_mph
        - LAG(median_speed_mph) OVER (
            PARTITION BY borough
            ORDER BY hour
        ) AS hour_delta,
    RANK() OVER (
        PARTITION BY borough
        ORDER BY
            CASE WHEN trips >= 1000 THEN median_speed_mph END ASC NULLS LAST,
            hour
    ) AS slowest_rank,
    FIRST_VALUE(hour) OVER (
        PARTITION BY borough
        ORDER BY
            CASE WHEN trips >= 1000 THEN median_speed_mph END ASC NULLS LAST,
            hour
    ) AS slowest_hour
FROM by_hour
ORDER BY borough, hour;
