-- Tip rate by payment type for in-policy 2024 trips.
-- Tip percent is tip_amount / (total_amount - tip_amount): the tip as a
-- share of the pre-tip bill. Cash tips are generally not recorded.
-- Grain: one row per payment type.
-- Windows: share of trips and rank by median tip percent.

WITH tipped AS (
    SELECT
        payment_type,
        payment_name,
        tip_amount,
        total_amount - tip_amount AS pretip
    FROM population
    WHERE payment_type IN (0, 1, 2, 3, 4)
      AND tip_amount >= 0
      AND total_amount > tip_amount
),
by_payment AS (
    SELECT
        payment_type,
        ANY_VALUE(payment_name) AS payment_name,
        COUNT(*) AS trips,
        AVG(tip_amount) AS avg_tip,
        MEDIAN(tip_amount) AS median_tip,
        AVG(tip_amount / pretip) AS avg_tip_pct,
        MEDIAN(tip_amount / pretip) AS median_tip_pct,
        AVG(CASE WHEN tip_amount > 0 THEN 1.0 ELSE 0.0 END) AS pct_with_tip
    FROM tipped
    GROUP BY payment_type
)
SELECT
    payment_type,
    payment_name,
    trips,
    trips * 1.0 / SUM(trips) OVER () AS trip_share,
    avg_tip,
    median_tip,
    avg_tip_pct,
    median_tip_pct,
    pct_with_tip,
    RANK() OVER (ORDER BY median_tip_pct DESC, payment_type) AS tip_rank
FROM by_payment
ORDER BY payment_type;
