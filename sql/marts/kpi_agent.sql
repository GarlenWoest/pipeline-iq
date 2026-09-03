-- kpi_agent.sql : rep leaderboard with a RANK() window function.
CREATE OR REPLACE VIEW kpi_agent AS
WITH closed AS (
    SELECT * FROM fct_pipeline WHERE is_closed
),
agg AS (
    SELECT
        sales_agent,
        manager,
        regional_office,
        COUNT(*)                                        AS closed_deals,
        SUM(CASE WHEN is_won THEN 1 ELSE 0 END)         AS won_deals,
        AVG(CASE WHEN is_won THEN 1.0 ELSE 0 END)       AS win_rate,
        SUM(close_value)                                AS revenue,
        AVG(cycle_days)                                 AS avg_cycle_days
    FROM closed
    GROUP BY sales_agent, manager, regional_office
)
SELECT
    *,
    RANK() OVER (ORDER BY revenue DESC)                 AS revenue_rank,
    RANK() OVER (ORDER BY win_rate DESC)                AS win_rate_rank
FROM agg
ORDER BY revenue DESC;
