-- kpi_monthly.sql : monthly bookings + a 3-month moving average and running
-- cumulative revenue, using window functions over the closed-won cohort.
CREATE OR REPLACE VIEW kpi_monthly AS
WITH won AS (
    SELECT activity_month, close_value
    FROM fct_pipeline
    WHERE is_won
),
monthly AS (
    SELECT
        activity_month,
        COUNT(*)          AS won_deals,
        SUM(close_value)  AS revenue
    FROM won
    GROUP BY activity_month
)
SELECT
    activity_month,
    won_deals,
    revenue,
    ROUND(AVG(revenue) OVER (
        ORDER BY activity_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0)   AS revenue_ma3,
    SUM(revenue) OVER (ORDER BY activity_month)          AS revenue_cumulative
FROM monthly
ORDER BY activity_month;
