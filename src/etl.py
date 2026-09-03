"""
etl.py
======
Builds the analytics warehouse: loads the four raw CSVs into DuckDB, then runs the
SQL transformation layer (staging -> marts) in dependency order. Everything is a
view, so the build is instant and always reflects the current CSVs.

Public helpers:
    build_warehouse(db_path)  -> duckdb.Connection with all models created
    q(con, sql)               -> run ad-hoc SQL, return a DataFrame
    table(con, name)          -> SELECT * FROM <model> as a DataFrame
"""
from __future__ import annotations

import glob
import os

import duckdb
import pandas as pd

RAW = "data/raw"
DB_PATH = "data/pipeline.duckdb"

RAW_TABLES = {
    "raw_accounts": f"{RAW}/accounts.csv",
    "raw_products": f"{RAW}/products.csv",
    "raw_sales_teams": f"{RAW}/sales_teams.csv",
    "raw_sales_pipeline": f"{RAW}/sales_pipeline.csv",
}

# SQL files executed in order. Staging must precede marts; fct precedes kpi_*.
SQL_ORDER = [
    "sql/staging/stg_accounts.sql",
    "sql/staging/stg_pipeline.sql",
    "sql/marts/dim_account.sql",
    "sql/marts/fct_pipeline.sql",
    "sql/marts/kpi_segment.sql",
    "sql/marts/kpi_agent.sql",
    "sql/marts/kpi_monthly.sql",
    "sql/marts/kpi_funnel.sql",
]


def _load_raw(con: duckdb.DuckDBPyConnection) -> None:
    for table, path in RAW_TABLES.items():
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Missing {path}. Run `python src/generate_data.py` first, or drop "
                f"the real Maven CSVs into {RAW}/.")
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv_auto('{path}', header=true, "
            f"all_varchar=true)")


def _run_sql_file(con: duckdb.DuckDBPyConnection, path: str) -> None:
    with open(path, "r", encoding="utf-8") as fh:
        con.execute(fh.read())


def build_warehouse(db_path: str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Create the DuckDB warehouse from CSVs + SQL models. Returns the connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = duckdb.connect(db_path)
    _load_raw(con)
    for sql_file in SQL_ORDER:
        _run_sql_file(con, sql_file)
    return con


def q(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def table(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    return con.execute(f"SELECT * FROM {name}").df()


def main() -> None:
    con = build_warehouse()
    models = [os.path.splitext(os.path.basename(p))[0] for p in SQL_ORDER]
    print(f"[etl] built warehouse at {DB_PATH}")
    print(f"[etl] models: {', '.join(models)}")
    n = con.execute("SELECT COUNT(*) FROM fct_pipeline").fetchone()[0]
    print(f"[etl] fct_pipeline rows = {n:,}")


if __name__ == "__main__":
    main()
