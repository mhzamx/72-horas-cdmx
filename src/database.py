from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

from .config import DB_PATH, ROOT

def _to_sql_safe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include=["datetime64[ns]"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out

def build_database(cases: pd.DataFrame, quality_flags: pd.DataFrame) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        _to_sql_safe(cases).to_sql("cases_raw", conn, index=False, if_exists="replace")
        quality_flags.astype({
            c: "int64" for c in quality_flags.columns if c != "case_key"
        }).to_sql("quality_flags", conn, index=False, if_exists="replace")

        schema = (ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8")
        views = (ROOT / "sql" / "02_views.sql").read_text(encoding="utf-8")
        conn.executescript(schema)
        conn.executescript(views)
        conn.commit()
    finally:
        conn.close()
    return DB_PATH
