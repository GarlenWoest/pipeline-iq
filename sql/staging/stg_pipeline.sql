-- stg_pipeline.sql : type-cast + derive opportunity-level fields.
-- One row per opportunity. Handles open deals (blank close_date / close_value).
CREATE OR REPLACE VIEW stg_pipeline AS
SELECT
    opportunity_id,
    sales_agent,
    product,
    account,
    deal_stage,
    CAST(engage_date AS DATE)                             AS engage_date,
    TRY_CAST(NULLIF(close_date, '') AS DATE)              AS close_date,
    TRY_CAST(NULLIF(close_value, '') AS INTEGER)          AS close_value,
    deal_stage = 'Won'                                    AS is_won,
    deal_stage IN ('Won', 'Lost')                         AS is_closed,
    deal_stage IN ('Prospecting', 'Engaging')             AS is_open,
    -- Sales-cycle length in days (closed deals only).
    CASE WHEN deal_stage IN ('Won', 'Lost')
         THEN date_diff('day',
                        CAST(engage_date AS DATE),
                        TRY_CAST(NULLIF(close_date, '') AS DATE))
    END                                                   AS cycle_days,
    date_trunc('month',
        COALESCE(TRY_CAST(NULLIF(close_date, '') AS DATE),
                 CAST(engage_date AS DATE)))              AS activity_month
FROM raw_sales_pipeline;
