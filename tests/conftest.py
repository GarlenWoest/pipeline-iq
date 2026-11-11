"""Shared fixture: build the full warehouse from synthetic data in a temp dir,
so tests never read or write anything inside the repo."""
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session")
def warehouse(tmp_path_factory):
    work = tmp_path_factory.mktemp("pipeline_iq")
    shutil.copytree(ROOT / "sql", work / "sql")
    (work / "data" / "raw").mkdir(parents=True)
    cwd = os.getcwd()
    os.chdir(work)
    try:
        import generate_data
        from etl import build_warehouse

        generate_data.main()
        con = build_warehouse()
        yield con
        con.close()
    finally:
        os.chdir(cwd)
