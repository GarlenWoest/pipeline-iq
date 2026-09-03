# Power BI Dashboard — Build Guide

The Python layer exports a clean **star schema** ready to import into Power BI with
zero transformation. This guide reproduces the 3-page executive dashboard.

> Run `python src/run_all.py` first — it writes the import files to
> `data/exports/powerbi/`.

## 1. Import the data

Import these three CSVs (**Home → Get data → Text/CSV**):

| File | Role | Grain |
|---|---|---|
| `fct_pipeline.csv` | Fact table | one row per opportunity |
| `dim_account.csv` | Account dimension | one row per account |
| `kpi_monthly.csv` | Pre-aggregated monthly bookings | one row per month |

**Model relationships (Model view):**
`dim_account[account]` 1 → * `fct_pipeline[account]` (single direction).
Mark `kpi_monthly[activity_month]` as a date column.

## 2. Core DAX measures

```DAX
Total Opportunities = COUNTROWS ( fct_pipeline )

Closed Deals = CALCULATE ( [Total Opportunities], fct_pipeline[is_closed] = TRUE )

Won Deals = CALCULATE ( [Total Opportunities], fct_pipeline[is_won] = TRUE )

Win Rate =
DIVIDE ( [Won Deals], [Closed Deals] )

Won Revenue =
CALCULATE ( SUM ( fct_pipeline[close_value] ), fct_pipeline[is_won] = TRUE )

Weighted Pipeline =
CALCULATE ( SUM ( fct_pipeline[weighted_open_value] ), fct_pipeline[is_open] = TRUE )

Avg Cycle (days) =
CALCULATE ( AVERAGE ( fct_pipeline[cycle_days] ), fct_pipeline[is_closed] = TRUE )

Avg Won Deal Size =
DIVIDE ( [Won Revenue], [Won Deals] )

-- Revenue concentration: share from the top 20% of accounts
Revenue Concentration Top 20% =
VAR RankedAccounts =
    ADDCOLUMNS ( VALUES ( dim_account[account] ), "@rev", [Won Revenue] )
VAR Cutoff =
    ROUNDUP ( COUNTROWS ( VALUES ( dim_account[account] ) ) * 0.2, 0 )
VAR TopRev =
    SUMX ( TOPN ( Cutoff, RankedAccounts, [@rev], DESC ), [@rev] )
RETURN
    DIVIDE ( TopRev, [Won Revenue] )
```

## 3. Page layout

### Page 1 — Executive summary
- **KPI cards:** Won Revenue, Win Rate, Closed Deals, Avg Cycle, Weighted Pipeline.
- **Line chart:** `kpi_monthly[revenue]` and `revenue_ma3` by month.
- **Slicers:** sector, regional office, revenue band.

### Page 2 — Pipeline funnel
- **Funnel/bar:** count by `deal_stage`.
- **Bar:** Win Rate by sector (add a company-average reference line).
- **Table:** rep leaderboard — Won Revenue, Win Rate, Avg Cycle, with a
  Win Rate data bar; sort by Won Revenue.

### Page 3 — Account segments
- **Matrix:** account tier (from `data/exports/account_segments.csv`, import as a
  4th table joined on `account`) × Won Revenue and account count.
- **Scatter:** frequency (x) vs. Won Revenue (y), colored by tier.
- **Drill-through:** account-level opportunity detail.

## 4. Export

Publish to Power BI Service or **File → Export → PDF**, then drop a screenshot of
Page 1 into `../assets/` as the dashboard hero and reference it in the root README.

> **Free-tier note:** all of the above works in Power BI Desktop (free). No Pro
> license is needed to build or export locally.
