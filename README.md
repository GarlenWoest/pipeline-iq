# Pipeline IQ — B2B Revenue & CRM Analytics

Sales pipeline analytics on 8,800 CRM opportunities: a SQL data model, account
segmentation, a backtested revenue forecast, and a model of what drives wins —
plus a Power BI dashboard and a short set of recommendations.

![Monthly bookings with backtested next-quarter forecast](assets/01_revenue_forecast.png)

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![SQL](https://img.shields.io/badge/SQL-DuckDB-lightgrey)
![Power BI](https://img.shields.io/badge/BI-Power%20BI-yellow)

**Question I set out to answer:** which segments, reps, and deals should the sales
team focus on next quarter, and what will we actually close?

---

## Headline findings

| Metric | Result |
|---|---|
| Total closed-won revenue | **$20.9M** across 8,397 closed deals |
| Overall win rate | **47.8%** |
| Best vs. worst sector win rate | **Technology 58.3%** vs. **Marketing 37.3%** — a **21-point** gap |
| Revenue concentration | Top **20%** of accounts drive **~27%** of revenue |
| Avg. sales cycle | **43.6 days** |
| Next-quarter bookings forecast | **$2.89M**, validated at **20.1% MAPE** (walk-forward backtest) |
| Open weighted pipeline | **$0.79M** |
| Win-driver model | Cross-validated **ROC-AUC 0.60** |

**Short version of the recommendation:** move prospecting effort from the
lowest-converting sectors (Marketing, Entertainment) toward Technology, Software,
and larger accounts, and give the top accounts — which drive ~27% of revenue —
named coverage. Full write-up in the [recommendation memo](reports/recommendation_memo.md).

---

## What's in it

- **SQL model** — a staging → marts warehouse in DuckDB (CTEs, window functions, a `fct_pipeline` + `dim_account` star schema).
- **Segmentation** — RFM adapted to B2B, clustered with K-means (k from silhouette score) into Strategic / Growth / Maintain / At-Risk tiers.
- **Forecast** — two simple methods compared with a walk-forward backtest; the better one, plus its error, sets the forecast band.
- **Win drivers** — a logistic model ranking what moves win rate (sector, deal size, account size, region).
- **BI** — a Power BI star-schema export and a build guide for the dashboard.

---

## Architecture

```
  data/raw/*.csv                4 relational CSVs (Maven CRM schema)
        │
        ▼
  DuckDB warehouse ── sql/staging/ (clean, type-cast, derive)
        │             sql/marts/   (fct_pipeline, dim_account, kpi_*)
        ▼
  Python analytics ── segmentation.py   RFM + K-means tiers
                      forecast.py       backtested bookings forecast
                      drivers.py        logistic win-driver model
        │
        ▼
  Outputs ── assets/*.png     charts (README + memo)
             data/exports/    segments, forecast, Power BI star schema
             reports/         metrics.json + recommendation memo
```

## Results gallery

| Pipeline funnel | Win rate by sector |
|---|---|
| ![funnel](assets/02_pipeline_funnel.png) | ![segments](assets/03_segment_winrate.png) |

| Account segments (RFM + K-means) | Win-rate drivers |
|---|---|
| ![account segments](assets/05_account_segments.png) | ![drivers](assets/06_win_drivers.png) |

---

## Quickstart

```bash
# 1. create the environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. run the whole project (data → warehouse → models → charts → exports)
python src/run_all.py
```

That single command regenerates the dataset, builds the DuckDB warehouse, runs
every model, writes all six charts to `assets/`, exports the Power BI star schema,
and refreshes `reports/metrics.json`. Run individual stages with:

```bash
python src/generate_data.py     # build the raw CSVs
python src/etl.py               # build the SQL warehouse
python src/segmentation.py      # account tiers
python src/forecast.py          # backtested forecast + method comparison
python src/drivers.py           # win-driver model
```

## Data

This repo includes a small data generator (`src/generate_data.py`) that builds
sample CSVs in the same shape as the free [Maven Analytics "CRM Sales
Opportunities"](https://www.mavenanalytics.io/data-playground) dataset — four
tables (`sales_pipeline`, `accounts`, `products`, `sales_teams`) — so it runs
without a download. Win rate in the sample data varies by sector, rep, deal size,
and account size, so there's real structure for the analysis to find. To use the
real data instead, download the four Maven CSVs into `data/raw/` and skip
`generate_data.py`; everything downstream reads the same file and column names.

## Repository structure

```
pipeline-iq/
├─ README.md
├─ requirements.txt
├─ data/
│  ├─ raw/            # 4 source CSVs
│  └─ exports/        # segments, forecast, Power BI star schema
├─ sql/
│  ├─ staging/        # stg_accounts, stg_pipeline (clean views)
│  └─ marts/          # fct_pipeline, dim_account, kpi_* (analytics views)
├─ src/
│  ├─ generate_data.py
│  ├─ etl.py          # loads CSVs → DuckDB, runs SQL layer
│  ├─ segmentation.py # RFM + K-means
│  ├─ forecast.py     # backtested bookings forecast
│  ├─ drivers.py      # logistic win-driver model
│  ├─ viz.py          # chart rendering
│  └─ run_all.py      # one-command reproduce
├─ notebooks/         # analysis walkthrough
├─ powerbi/           # dashboard build guide + DAX measures
├─ reports/           # metrics.json + recommendation memo
└─ assets/            # exported charts
```

## Tech stack

**Python** (pandas, numpy, scikit-learn, matplotlib) · **SQL** (DuckDB) · **Power BI** · isolated `venv`.

## Notes & limitations

- The headline numbers are computed from the shipped dataset and refresh whenever
  `run_all.py` runs; they match exactly what the script prints.
- The forecast deliberately favors transparent, backtestable methods over
  black-box models, which suits a ~24-month monthly series where the backtest
  needs to be trustworthy.
- Point it at real Maven (or a Salesforce/HubSpot export) CSVs for a live read.
