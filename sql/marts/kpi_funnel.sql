-- kpi_funnel.sql : deal-stage funnel with count + total (weighted) value.
CREATE OR REPLACE VIEW kpi_funnel AS
SELECT
    deal_stage,
    COUNT(*)                                            AS opportunities,
    SUM(list_price)                                     AS gross_pipeline_value,
    SUM(weighted_open_value)                            AS weighted_pipeline_value
FROM fct_pipeline
GROUP BY deal_stage
ORDER BY CASE deal_stage
    WHEN 'Prospecting' THEN 1 WHEN 'Engaging' THEN 2
    WHEN 'Won' THEN 3 WHEN 'Lost' THEN 4 END;
