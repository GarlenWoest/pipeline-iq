"""Segment accounts with RFM + K-means. RFM is adapted to B2B sales:
    Recency   = days since the account's most recent opportunity
    Frequency = number of opportunities with the account
    Monetary  = total won revenue from the account
Features are standardized and clustered with K-means (k picked by silhouette
score); each cluster gets a business tier. Returns one row per account.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from etl import build_warehouse, table

# KMeans triggers harmless "matmul" RuntimeWarnings on macOS (Accelerate BLAS);
# results are fine, so quiet just those.
warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)


def _rfm_frame(con) -> pd.DataFrame:
    fct = table(con, "fct_pipeline")
    fct["engage_date"] = pd.to_datetime(fct["engage_date"])
    asof = fct["engage_date"].max()

    grp = fct.groupby("account")
    rfm = pd.DataFrame({
        "recency_days": (asof - grp["engage_date"].max()).dt.days,
        "frequency": grp["opportunity_id"].count(),
        "monetary": grp.apply(
            lambda d: d.loc[d["is_won"], "close_value"].sum(), include_groups=False),
    })
    # Attach a couple of firmographics for interpretation.
    firmo = fct.groupby("account").agg(
        sector=("sector", "first"),
        revenue_band=("revenue_band", "first")).reset_index()
    return rfm.reset_index().merge(firmo, on="account")


def _rfm_scores(rfm: pd.DataFrame) -> pd.DataFrame:
    # 1-5 quintile scores. Recency is reversed (more recent = better).
    def score(series, reverse=False):
        ranks = series.rank(method="first")
        q = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
        return 6 - q if reverse else q

    rfm = rfm.copy()
    rfm["R"] = score(rfm["recency_days"], reverse=True)
    rfm["F"] = score(rfm["frequency"])
    rfm["M"] = score(rfm["monetary"])
    rfm["rfm_score"] = rfm[["R", "F", "M"]].sum(axis=1)
    return rfm


def _best_k(X: np.ndarray, k_range=range(3, 7)) -> int:
    best_k, best_s = 3, -1.0
    for k in k_range:
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
        s = silhouette_score(X, labels)
        if s > best_s:
            best_k, best_s = k, s
    return best_k


def _label_tiers(rfm: pd.DataFrame) -> pd.DataFrame:
    """Map clusters to ordered business tiers by mean RFM score."""
    order = (rfm.groupby("cluster")["rfm_score"].mean()
             .sort_values(ascending=False).index.tolist())
    names = ["Strategic", "Growth", "Maintain", "At-Risk", "Dormant", "Marginal"]
    mapping = {c: names[i] for i, c in enumerate(order)}
    rfm["tier"] = rfm["cluster"].map(mapping)
    return rfm


def segment_accounts(con=None) -> pd.DataFrame:
    con = con or build_warehouse()
    rfm = _rfm_scores(_rfm_frame(con))

    features = ["recency_days", "frequency", "monetary"]
    X = StandardScaler().fit_transform(rfm[features])
    k = _best_k(X)
    rfm["cluster"] = KMeans(n_clusters=k, n_init=10,
                            random_state=42).fit_predict(X)
    rfm = _label_tiers(rfm)
    return rfm.sort_values("rfm_score", ascending=False).reset_index(drop=True)


def main() -> None:
    seg = segment_accounts()
    seg.to_csv("data/exports/account_segments.csv", index=False)
    summary = (seg.groupby("tier")
               .agg(accounts=("account", "count"),
                    avg_rfm=("rfm_score", "mean"),
                    total_won_revenue=("monetary", "sum"))
               .sort_values("avg_rfm", ascending=False))
    print("[segmentation] tiers:")
    print(summary.round(1).to_string())
    print(f"[segmentation] wrote data/exports/account_segments.csv "
          f"({len(seg)} accounts)")


if __name__ == "__main__":
    main()
