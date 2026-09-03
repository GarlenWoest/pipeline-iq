"""
generate_data.py
================
Creates a realistic synthetic B2B sales-pipeline dataset that mirrors the schema
of the free Maven Analytics "CRM Sales Opportunities" dataset, so this repo runs
end-to-end with zero external downloads.

To use the REAL data instead: download the four CSVs from Maven Analytics
(sales_pipeline, accounts, products, sales_teams), drop them in data/raw/, and
skip this script. The rest of the pipeline reads the same file/column names.

Output (data/raw/):
  accounts.csv        one row per customer account (firmographics)
  products.csv        product catalog with list prices
  sales_teams.csv     sales agents -> manager -> regional office
  sales_pipeline.csv  one row per opportunity (the fact table)

The generator intentionally bakes in *learnable* structure — win rate varies by
sector, agent, and deal size; cycle length varies by product — so the analytics
downstream surface real, defensible patterns rather than noise.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
OUT = "data/raw"

# ----------------------------------------------------------------------------
# Reference dimensions
# ----------------------------------------------------------------------------
SECTORS = [
    "technology", "medical", "software", "finance", "retail",
    "telecommunications", "employment", "services", "entertainment", "marketing",
]
# Baseline win-rate lift by sector (before deal-size / agent effects).
SECTOR_WIN_BIAS = {
    "technology": 0.10, "software": 0.08, "finance": 0.05, "medical": 0.03,
    "telecommunications": 0.02, "services": 0.00, "retail": -0.02,
    "employment": -0.03, "marketing": -0.04, "entertainment": -0.06,
}
REGIONS = ["Central", "East", "West"]

PRODUCTS = [
    # (product, series, list_price)
    ("GTX Basic", "GTX", 550),
    ("GTX Pro", "GTX", 4821),
    ("GTX Plus Pro", "GTX", 5482),
    ("GTX Plus Basic", "GTX", 1096),
    ("MG Special", "MG", 55),
    ("MG Advanced", "MG", 3393),
    ("GTK 500", "GTK", 26768),   # enterprise flagship
    ("GTXPro", "GTX", 4821),
]
# Longer sales cycles for bigger-ticket series.
SERIES_CYCLE_DAYS = {"GTX": 42, "MG": 28, "GTK": 88}


def make_accounts(n: int = 85) -> pd.DataFrame:
    names = [f"{prefix}{i:03d}" for i, prefix in
             zip(range(n), RNG.choice(list("ABCDEFGHJKLMNPRSTUVWXYZ"), n))]
    sectors = RNG.choice(SECTORS, n, p=_norm([3, 2, 3, 2, 2, 1, 1, 2, 1, 1]))
    revenue = np.round(RNG.lognormal(mean=6.4, sigma=1.0, size=n), 2)  # $M
    employees = (revenue * RNG.uniform(3, 9, n)).astype(int).clip(20, 45000)
    df = pd.DataFrame({
        "account": [f"Account_{n_}" for n_ in names],
        "sector": sectors,
        "year_established": RNG.integers(1975, 2018, n),
        "revenue": revenue,
        "employees": employees,
        "office_location": RNG.choice(
            ["United States", "United States", "United States",
             "Korea", "Germany", "Japan", "Philippines", "Brazil"], n),
        "subsidiary_of": np.where(RNG.random(n) < 0.12, "Acme Holdings", ""),
    })
    return df


def make_products() -> pd.DataFrame:
    seen, rows = set(), []
    for product, series, price in PRODUCTS:
        if product in seen:
            continue
        seen.add(product)
        rows.append({"product": product, "series": series, "sales_price": price})
    return pd.DataFrame(rows)


def make_sales_teams(n_agents: int = 30) -> pd.DataFrame:
    managers = [f"Manager_{i}" for i in range(1, 7)]
    rows = []
    for i in range(n_agents):
        mgr = managers[i % len(managers)]
        rows.append({
            "sales_agent": f"Agent_{i+1:02d}",
            "manager": mgr,
            "regional_office": REGIONS[i % len(REGIONS)],
        })
    return pd.DataFrame(rows)


def make_pipeline(accounts, products, teams, n: int = 8800) -> pd.DataFrame:
    # Per-agent skill: a latent win-rate multiplier (some reps are just better).
    agent_skill = {a: s for a, s in
                   zip(teams["sales_agent"],
                       RNG.normal(0.0, 0.08, len(teams)))}
    # Enterprise accounts convert better (dedicated buying process); SMBs churn.
    band_effect = {"Enterprise": 0.06, "Mid-Market": 0.02, "SMB": -0.04}

    acc = accounts.set_index("account")
    prod = products.set_index("product")
    prod_list = products["product"].to_numpy()
    agent_list = teams["sales_agent"].to_numpy()

    # Analysis window: a clean 24-month span. We assign each CLOSED deal a
    # close-month first (so monthly bookings are mature, with no right-censoring
    # ramp/tail artifact), then derive engage_date = close_date - cycle. Open
    # deals are engaged near the snapshot end and have no close yet.
    window_start = pd.Timestamp("2024-01-01")
    n_months = 24
    month_starts = [window_start + pd.DateOffset(months=k) for k in range(n_months)]
    snapshot = month_starts[-1] + pd.offsets.MonthEnd(0)
    # Close-month weights: gentle +1.2%/month growth trend x Q4 (Oct-Dec) bump.
    month_weight = np.array([
        (1 + 0.012 * k) * (1.15 if (window_start + pd.DateOffset(months=k)).month
                           in (10, 11, 12) else 1.0)
        for k in range(n_months)])
    month_weight = month_weight / month_weight.sum()

    rows = []
    for i in range(n):
        product = RNG.choice(prod_list)
        series = prod.loc[product, "series"]
        list_price = float(prod.loc[product, "sales_price"])
        account = RNG.choice(accounts["account"].to_numpy())
        sector = acc.loc[account, "sector"]
        acct_rev = float(acc.loc[account, "revenue"])
        band = ("Enterprise" if acct_rev >= 5000
                else "Mid-Market" if acct_rev >= 1000 else "SMB")
        agent = RNG.choice(agent_list)

        # --- win probability model (this is the signal analysts will recover) ---
        base = 0.46
        p = base + 1.4 * SECTOR_WIN_BIAS[sector] + agent_skill[agent]
        p += band_effect[band]
        # Bigger deals close less often.
        p += -0.08 * (np.log1p(list_price) - 7) / 3
        p = float(np.clip(p, 0.06, 0.92))

        cycle = max(3, int(RNG.normal(SERIES_CYCLE_DAYS[series],
                                      SERIES_CYCLE_DAYS[series] * 0.35)))

        # ~4.5% of opportunities are still open (engaged recently, not yet closed).
        if RNG.random() < 0.045:
            stage = RNG.choice(["Prospecting", "Engaging"], p=[0.45, 0.55])
            engage = snapshot - pd.Timedelta(days=int(RNG.integers(3, 70)))
            close_date, close_value = pd.NaT, np.nan
        else:
            won = RNG.random() < p
            stage = "Won" if won else "Lost"
            m_idx = RNG.choice(n_months, p=month_weight)
            month0 = month_starts[m_idx]
            day = int(RNG.integers(0, 27))
            close_date = month0 + pd.Timedelta(days=day)
            engage = close_date - pd.Timedelta(days=cycle)
            if won:
                # Realized value scatters around list (discounts + upsell).
                close_value = round(list_price * RNG.uniform(0.82, 1.12), 0)
            else:
                close_value = 0.0

        rows.append({
            "opportunity_id": f"OPP{i+1:06d}",
            "sales_agent": agent,
            "product": product,
            "account": account,
            "deal_stage": stage,
            "engage_date": engage.date().isoformat(),
            "close_date": close_date.date().isoformat()
            if pd.notna(close_date) else "",
            "close_value": "" if pd.isna(close_value) else int(close_value),
        })
    return pd.DataFrame(rows)


def _norm(x):
    x = np.asarray(x, dtype=float)
    return x / x.sum()


def main() -> None:
    accounts = make_accounts()
    products = make_products()
    teams = make_sales_teams()
    pipeline = make_pipeline(accounts, products, teams)

    accounts.to_csv(f"{OUT}/accounts.csv", index=False)
    products.to_csv(f"{OUT}/products.csv", index=False)
    teams.to_csv(f"{OUT}/sales_teams.csv", index=False)
    pipeline.to_csv(f"{OUT}/sales_pipeline.csv", index=False)

    won = (pipeline["deal_stage"] == "Won").sum()
    closed = pipeline["deal_stage"].isin(["Won", "Lost"]).sum()
    print(f"[generate_data] accounts={len(accounts)} products={len(products)} "
          f"agents={len(teams)} opportunities={len(pipeline)}")
    print(f"[generate_data] overall win rate = {won/closed:0.1%} "
          f"({won:,} won / {closed:,} closed)")
    print(f"[generate_data] wrote 4 CSVs to {OUT}/")


if __name__ == "__main__":
    main()
