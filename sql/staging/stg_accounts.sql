-- stg_accounts.sql : clean firmographics + a simple revenue band for slicing.
CREATE OR REPLACE VIEW stg_accounts AS
SELECT
    account,
    lower(trim(sector))                       AS sector,
    CAST(year_established AS INTEGER)          AS year_established,
    CAST(revenue AS DOUBLE)                    AS revenue,   -- $M
    CAST(employees AS INTEGER)                 AS employees,
    office_location,
    NULLIF(subsidiary_of, '')                 AS subsidiary_of,
    CASE
        WHEN CAST(revenue AS DOUBLE) >= 5000 THEN 'Enterprise'
        WHEN CAST(revenue AS DOUBLE) >= 1000 THEN 'Mid-Market'
        ELSE 'SMB'
    END                                       AS revenue_band
FROM raw_accounts;
