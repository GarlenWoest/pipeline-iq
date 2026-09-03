-- kpi_segment.sql : win-rate + value KPIs by sector (CTE + aggregation).
CREATE OR REPLACE VIEW kpi_segment AS
WITH closed AS (
    SELECT * FROM fct_pipeline WHERE is_closed
)
SELECT
    sector,
    COUNT(*)                                          AS opportunities,
    SUM(CASE WHEN is_won THEN 1 ELSE 0 END)           AS won,
    ROUND(AVG(CASE WHEN is_won THEN 1.0 ELSE 0 END), 4) AS win_rate,
    SUM(close_value)                                  AS revenue,
    ROUND(AVG(CASE WHEN is_won THEN close_value END), 0) AS avg_won_deal,
    ROUND(AVG(cycle_days), 1)                         AS avg_cycle_days
FROM closed
GROUP BY sector
ORDER BY revenue DESC;
