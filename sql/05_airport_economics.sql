-- Airport trip economics, including the JFK flat fare (RatecodeID 2).
-- A trip is assigned to the airport at the pickup end when the pickup is
-- an airport, otherwise to the airport at the dropoff.
-- Grain: airport x fare product x direction.
-- Windows: share of that airport's trips, and rank within the airport.

WITH airport_trips AS (
    SELECT
        CASE
            WHEN PULocationID = 132 THEN 'JFK'
            WHEN PULocationID = 138 THEN 'LGA'
            WHEN PULocationID = 1 THEN 'EWR'
            WHEN DOLocationID = 132 THEN 'JFK'
            WHEN DOLocationID = 138 THEN 'LGA'
            WHEN DOLocationID = 1 THEN 'EWR'
        END AS airport,
        CASE
            WHEN RatecodeID = 1 THEN 'Standard'
            WHEN RatecodeID = 2 THEN 'JFK flat'
            WHEN RatecodeID = 3 THEN 'Newark'
            WHEN RatecodeID IS NULL THEN 'Rate missing'
            ELSE 'Other'
        END AS product,
        CASE
            WHEN PULocationID IN (1, 132, 138)
             AND DOLocationID IN (1, 132, 138) THEN 'airport to airport'
            WHEN PULocationID IN (1, 132, 138)
             AND do_borough = 'Manhattan' THEN 'to Manhattan'
            WHEN DOLocationID IN (1, 132, 138)
             AND pu_borough = 'Manhattan' THEN 'from Manhattan'
            WHEN PULocationID IN (1, 132, 138) THEN 'to other'
            ELSE 'from other'
        END AS direction,
        fare_amount,
        total_amount,
        tip_amount,
        tolls_amount,
        trip_distance,
        duration_sec
    FROM population
    WHERE PULocationID IN (1, 132, 138)
       OR DOLocationID IN (1, 132, 138)
),
aggregated AS (
    SELECT
        airport,
        product,
        direction,
        COUNT(*) AS trips,
        MEDIAN(fare_amount) AS median_fare,
        MEDIAN(total_amount) AS median_total,
        MEDIAN(trip_distance) AS median_miles,
        MEDIAN(duration_sec) / 60.0 AS median_minutes,
        MEDIAN(fare_amount / trip_distance) AS median_fare_per_mile,
        MEDIAN(tip_amount) AS median_tip,
        MEDIAN(tolls_amount) AS median_tolls,
        AVG(tip_amount / NULLIF(total_amount - tip_amount, 0)) AS avg_tip_pct,
        AVG(CASE WHEN trip_distance < 5 THEN 1.0 ELSE 0.0 END) AS pct_under_5_miles
    FROM airport_trips
    WHERE airport IS NOT NULL
    GROUP BY airport, product, direction
)
SELECT
    airport,
    product,
    direction,
    trips,
    median_fare,
    median_total,
    median_miles,
    median_minutes,
    median_fare_per_mile,
    median_tip,
    median_tolls,
    avg_tip_pct,
    pct_under_5_miles,
    trips * 1.0 / SUM(trips) OVER (PARTITION BY airport) AS share_of_airport,
    RANK() OVER (
        PARTITION BY airport
        ORDER BY trips DESC, product, direction
    ) AS rank_in_airport
FROM aggregated
ORDER BY airport, rank_in_airport, direction;
