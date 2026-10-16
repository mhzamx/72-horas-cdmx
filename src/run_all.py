from __future__ import annotations
import json
from pathlib import Path

from .config import PROCESSED_DIR, OUTPUT_TABLES
from .ingest import load_cases
from .quality import build_quality_flags, quality_summary
from .database import build_database
from .analysis import (
    export_sql_kpis,
    export_time_distribution,
    export_reporting_delay_distribution,
    export_survival_snapshot,
    export_survival_by_group,
    export_pressure_signals,
    export_quality_detail,
)
from .charts import make_charts, make_outcome_charts
from .powerbi_export import export_powerbi_tables
from .outcomes import (
    export_outcome_audit,
    export_outcome_intervals,
    export_outcome_group_kpis,
    export_outcome_competing_risk,
)

TOTAL_STEPS = 16


def main():
    print(f"[1/{TOTAL_STEPS}] Leyendo fuente...")
    cases, metadata = load_cases()

    print(f"[2/{TOTAL_STEPS}] Validando calidad...")
    report_window_start = cases["report_date"].min()
    flags = build_quality_flags(cases, report_window_start=report_window_start)
    summary = quality_summary(flags)

    print(f"[3/{TOTAL_STEPS}] Construyendo SQLite...")
    db = build_database(cases, flags)

    print(f"[4/{TOTAL_STEPS}] Exportando KPI SQL...")
    export_sql_kpis()

    print(f"[5/{TOTAL_STEPS}] Calculando distribución de tiempos...")
    export_time_distribution()
    export_reporting_delay_distribution()

    print(f"[6/{TOTAL_STEPS}] Calculando supervivencia (general y por grupo)...")
    export_survival_snapshot()
    export_survival_by_group("sex")
    export_survival_by_group("borough_missing")
    export_survival_by_group("age_group")

    print(f"[7/{TOTAL_STEPS}] Detectando presión operativa...")
    export_pressure_signals()

    print(f"[8/{TOTAL_STEPS}] Documentando casos con flags de calidad...")
    export_quality_detail()
    # Se escribe ANTES de make_charts(): el gráfico 06_data_quality.png
    # lee este CSV. Escribirlo después hacía que ese gráfico se saltara
    # en silencio (el archivo aún no existía) sin lanzar ningún error.
    summary.to_csv(
        OUTPUT_TABLES / "data_quality_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(f"[9/{TOTAL_STEPS}] Generando gráficos...")
    make_charts()

    print(f"[10/{TOTAL_STEPS}] Exportando tablas para Power BI...")
    export_powerbi_tables()

    # --- Ampliación: desenlaces CON VIDA / SIN VIDA (ver src/outcomes.py) ---
    print(f"[11/{TOTAL_STEPS}] Auditando location_condition y desenlaces por intervalo...")
    export_outcome_audit()
    export_outcome_intervals()
    export_outcome_group_kpis()

    print(f"[12/{TOTAL_STEPS}] Calculando riesgos competitivos (Aalen-Johansen)...")
    export_outcome_competing_risk()

    print(f"[13/{TOTAL_STEPS}] Generando gráficos de desenlaces...")
    make_outcome_charts()

    # --- v0.2: población completa E0-E3 (doc 03; src/estimands.py) ---
    print(f"[14/{TOTAL_STEPS}] v0.2: clases de población, escenarios E0-E3, Aalen-Johansen exacto por escenario...")
    from .estimands import run_v02
    res = run_v02()

    print(f"[15/{TOTAL_STEPS}] v0.2: exportando tablas para Power BI (dashboard/data_v02)...")
    from .powerbi_export_v02 import export_powerbi_tables_v02
    export_powerbi_tables_v02(res["v"])

    print(f"[16/{TOTAL_STEPS}] v0.2: generando gráficas 10-12...")
    from .charts_v02 import make_charts_v02
    make_charts_v02()

    (PROCESSED_DIR / "source_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print("")
    print("LISTO")
    print(f"Base SQLite: {db}")
    print("Resultados: outputs/tables, outputs/charts y dashboard/data")

if __name__ == "__main__":
    main()
