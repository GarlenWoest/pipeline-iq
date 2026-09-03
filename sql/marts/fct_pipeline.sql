-- fct_pipeline.sql : the central analytics model. One row per opportunity,
-- enriched with account, product, and sales-team attributes. This is the single
-- table Power BI and the Python layer read from.
CREATE OR REPLACE VIEW fct_pipeline AS
SELECT
    p.opportunity_id,
    p.deal_stage,
    p.is_won,
    p.is_closed,
    p.is_open,
    p.engage_date,
    p.close_date,
    p.activity_month,
    p.cycle_days,
    p.close_value,
    -- Weighted pipeline value for OPEN deals: list price x stage probability.
    CASE p.deal_stage
        WHEN 'Prospecting' THEN CAST(pr.sales_price AS DOUBLE) * 0.20
        WHEN 'Engaging'    THEN CAST(pr.sales_price AS DOUBLE) * 0.45
        ELSE 0
    END                                       AS weighted_open_value,
    -- Account attributes
    a.account,
    a.sector,
    a.revenue_band,
    a.office_location,
    -- Product attributes
    p.product,
    pr.series,
    CAST(pr.sales_price AS DOUBLE)            AS list_price,
    -- Sales-team attributes
    t.sales_agent,
    t.manager,
    t.regional_office
FROM stg_pipeline p
LEFT JOIN dim_account a  ON a.account = p.account
LEFT JOIN raw_products pr ON pr.product = p.product
LEFT JOIN raw_sales_teams t ON t.sales_agent = p.sales_agent;
