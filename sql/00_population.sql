-- In-policy trips used by the KPI queries.
-- Calendar-year 2024 yellow trips with a positive fare and distance,
-- a completed duration of at most three hours, and a positive total.
-- Data-quality and anomaly queries intentionally read trips_enriched
-- instead, so they can see the rows this filter removes.
CREATE OR REPLACE VIEW population AS
SELECT *
FROM trips_enriched
WHERE pickup_in_2024
  AND duration_sec BETWEEN 1 AND 10800
  AND trip_distance > 0
  AND trip_distance <= 100
  AND fare_amount > 0
  AND fare_amount <= 300
  AND total_amount > 0;
