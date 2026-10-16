"""v0.2 — Tablas para Power BI (doc 03 §10). No modifica dashboard/data/ (v79)."""
from __future__ import annotations
import shutil
import pandas as pd

from .config import DASHBOARD_DATA, DASHBOARD_DATA_V02, OUTPUT_TABLES

V02_TABLES = [
    "km_scenarios_v02.csv", "km_curve_e3_v02.csv", "cif_exact_v02.csv",
    "cif_summary_v02.csv", "outcome_cif_summary.csv", "group_kpis_v02.csv",
    "population_classes_v02.csv", "data_quality_summary.csv",
    "outcome_by_sex.csv", "outcome_by_age_group.csv", "outcome_by_borough.csv",
    "outcome_intervals_report_clock.csv",
]


def export_powerbi_tables_v02(v: pd.DataFrame) -> None:
    for name in V02_TABLES:
        shutil.copyfile(OUTPUT_TABLES / name, DASHBOARD_DATA_V02 / name)
    for name in ("dim_date.csv", "dim_borough.csv"):
        shutil.copyfile(DASHBOARD_DATA / name, DASHBOARD_DATA_V02 / name)
    # fact_cases v0.2 = fact_cases v79 + clase de población. USO LOCAL ÚNICAMENTE
    # (es por caso): no publicar el .pbix con esta tabla (doc 03 §10, H7).
    fact = pd.read_csv(DASHBOARD_DATA / "fact_cases.csv", encoding="utf-8-sig")
    cls = v[["case_key", "population_class"]]
    fact.merge(cls, on="case_key", how="left").to_csv(
        DASHBOARD_DATA_V02 / "fact_cases_LOCAL_v02.csv", index=False, encoding="utf-8-sig")
