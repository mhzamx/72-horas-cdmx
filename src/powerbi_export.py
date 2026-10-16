from __future__ import annotations

import sqlite3
import pandas as pd

from .config import DB_PATH, DASHBOARD_DATA

# ---------------------------------------------------------------------------
# Exporta un esquema en estrella simple para Power BI:
#   fact_cases   -> un registro por caso (grano = case_key)
#   dim_date     -> una fila por fecha del calendario cubierto por los datos
#   dim_borough  -> una fila por alcaldía de la desaparición
#
# sexo y grupo de edad se dejan como atributos planos en fact_cases (no se
# crean dim_sex / dim_age_group): con solo 2 y 6 valores respectivamente,
# separarlos en tablas aparte no añade valor analítico y solo complica el
# modelo. Ver dashboard/POWER_BI_GUIDE.md para la justificación completa.
# ---------------------------------------------------------------------------


def _query(sql: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


def _date_key(series: pd.Series) -> pd.Series:
    """Convierte una fecha a clave YYYYMMDD como entero anulable (Int64),
    para que Power BI no la muestre con decimales (".0") cuando hay NaN."""
    dt = pd.to_datetime(series, errors="coerce")
    key = dt.dt.strftime("%Y%m%d")
    return pd.to_numeric(key, errors="coerce").astype("Int64")


def export_fact_cases() -> pd.DataFrame:
    df = _query("""
        SELECT
            case_key, source_id, report_date, missing_date, location_date,
            status, is_located, sex, age, age_group, nationality,
            borough_missing, borough_location, report_source,
            location_condition, health_status,
            event_to_report_days, report_to_location_days, missing_to_location_days,
            valid_for_report_timeline, valid_for_missing_timeline,
            excluded_from_report_timeline_reason,
            location_before_report, location_before_event, report_before_event,
            status_located_without_location_date, duplicate_content,
            historic_missing_date
        FROM vw_cases
    """)
    df["report_date_key"] = _date_key(df["report_date"])
    df["missing_date_key"] = _date_key(df["missing_date"])
    df["location_date_key"] = _date_key(df["location_date"])
    df.to_csv(DASHBOARD_DATA / "fact_cases.csv", index=False, encoding="utf-8-sig")
    return df


def export_dim_date(dates: pd.Series) -> pd.DataFrame:
    valid = pd.to_datetime(dates, errors="coerce").dropna()
    if valid.empty:
        out = pd.DataFrame(columns=[
            "date_key", "date", "year", "quarter", "month", "month_name", "day", "iso_week"
        ])
        out.to_csv(DASHBOARD_DATA / "dim_date.csv", index=False, encoding="utf-8-sig")
        return out

    full_range = pd.date_range(valid.min().normalize(), valid.max().normalize(), freq="D")
    out = pd.DataFrame({"date": full_range})
    out["date_key"] = out["date"].dt.strftime("%Y%m%d").astype("int64")
    out["year"] = out["date"].dt.year
    out["quarter"] = out["date"].dt.quarter
    out["month"] = out["date"].dt.month
    out["month_name"] = out["date"].dt.strftime("%B")
    out["day"] = out["date"].dt.day
    out["iso_week"] = out["date"].dt.isocalendar().week
    out = out[["date_key", "date", "year", "quarter", "month", "month_name", "day", "iso_week"]]
    out.to_csv(DASHBOARD_DATA / "dim_date.csv", index=False, encoding="utf-8-sig")
    return out


def export_dim_borough() -> pd.DataFrame:
    df = _query("""
        SELECT
            borough_missing,
            sample_size,
            located_records,
            open_records,
            pct_located_le_3d_among_located,
            avg_report_to_location_days
        FROM vw_borough_kpis
        WHERE borough_missing IS NOT NULL
    """)
    df["below_min_sample_size"] = (df["sample_size"] < 30).astype(int)
    df.to_csv(DASHBOARD_DATA / "dim_borough.csv", index=False, encoding="utf-8-sig")
    return df


def export_powerbi_tables() -> None:
    fact = export_fact_cases()
    all_dates = pd.concat([
        fact["report_date"], fact["missing_date"], fact["location_date"]
    ], ignore_index=True)
    export_dim_date(all_dates)
    export_dim_borough()
