"""Logistic regression over closed deals to see what moves win probability
(deal size, sector, region, product series, account size). Coefficients rank the
drivers; cross-validated ROC-AUC shows how predictable win/loss is."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from etl import build_warehouse, table

NUMERIC = ["log_list_price"]
CATEGORICAL = ["sector", "regional_office", "series", "revenue_band"]


def _prep(con) -> pd.DataFrame:
    fct = table(con, "fct_pipeline")
    df = fct[fct["is_closed"]].copy()
    df["log_list_price"] = np.log1p(df["list_price"].astype(float))
    df["y"] = df["is_won"].astype(int)
    return df.dropna(subset=CATEGORICAL + NUMERIC + ["y"])


def fit_driver_model(con=None) -> dict:
    con = con or build_warehouse()
    df = _prep(con)
    X, y = df[NUMERIC + CATEGORICAL], df["y"]

    pre = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), CATEGORICAL),
    ])
    model = Pipeline([("pre", pre),
                      ("clf", LogisticRegression(max_iter=1000, C=1.0))])

    # cross-validated AUC (no train-on-test leakage)
    proba = cross_val_predict(model, X, y, cv=5, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, proba)

    model.fit(X, y)
    names = model.named_steps["pre"].get_feature_names_out()
    coefs = model.named_steps["clf"].coef_[0]
    drivers = (pd.DataFrame({"feature": names, "coef": coefs})
               .assign(odds_ratio=lambda d: np.exp(d["coef"]),
                       abs_coef=lambda d: d["coef"].abs())
               .sort_values("abs_coef", ascending=False)
               .drop(columns="abs_coef")
               .reset_index(drop=True))
    return {"auc": float(auc), "drivers": drivers, "n": len(df)}


def main() -> None:
    out = fit_driver_model()
    out["drivers"].to_csv("data/exports/win_drivers.csv", index=False)
    print(f"[drivers] cross-validated ROC-AUC = {out['auc']:0.3f} "
          f"(n={out['n']:,} closed deals)")
    print("[drivers] top drivers (by |coef|):")
    print(out["drivers"].head(8).round(3).to_string(index=False))
    print("[drivers] wrote data/exports/win_drivers.csv")


if __name__ == "__main__":
    main()
