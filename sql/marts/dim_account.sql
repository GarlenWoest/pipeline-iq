-- dim_account.sql : conformed account dimension used by the fact table and BI.
CREATE OR REPLACE VIEW dim_account AS
SELECT
    a.account,
    a.sector,
    a.revenue_band,
    a.revenue,
    a.employees,
    a.office_location,
    a.subsidiary_of,
    (2025 - a.year_established)               AS account_age_years
FROM stg_accounts a;
