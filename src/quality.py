from __future__ import annotations
import pandas as pd

# ---------------------------------------------------------------------------
# Reglas de calidad.
#
# Principio del proyecto: un flag de calidad NO es lo mismo que "borrar el
# caso". Ninguna regla de este archivo elimina filas; solo las marca. Las
# decisiones de qué casos entran en qué análisis se toman después, en las
# vistas SQL (sql/02_views.sql), donde quedan documentadas como criterios
# de población explícitos.
#
# Las reglas se dividen en categorías con implicaciones distintas:
#
#   MISSING     -> falta un dato necesario para cierto análisis.
#   IMPOSSIBLE  -> el orden de las fechas es lógicamente imposible
#                  (ej. localizado antes de haber desaparecido). Esto sí
#                  es un problema de captura.
#   AMBIGUOUS   -> el orden es "raro" pero tiene una explicación legítima
#                  y NO debe tratarse como error automáticamente. El caso
#                  típico: location_date < report_date, que puede ocurrir
#                  porque la persona fue localizada antes de que la
#                  Comisión registrara formalmente el reporte.
#   MISMATCH    -> el estatus declarado no es consistente con las fechas
#                  capturadas (ej. status=LOCALIZADO sin fecha de
#                  localización utilizable).
#   DUPLICATE   -> el registro es idéntico a otro salvo el identificador.
#   OUTLIER     -> el valor es extremo pero plausible (ej. una
#                  desaparición ocurrida hace décadas, típico de casos de
#                  larga data que se incorporan al registro después).
# ---------------------------------------------------------------------------

FLAG_CATEGORY = {
    "missing_report_date": "MISSING",
    "missing_event_date": "MISSING",
    "missing_location_date": "MISSING",
    "missing_borough": "MISSING",
    "location_before_event": "IMPOSSIBLE",
    "report_before_event": "IMPOSSIBLE",
    "location_before_report": "AMBIGUOUS",
    "status_located_without_location_date": "MISMATCH",
    "status_missing_with_location_date": "MISMATCH",
    "duplicate_content": "DUPLICATE",
    "historic_missing_date": "OUTLIER",
}

# Un caso "desaparecido hace mucho tiempo" se define aquí como uno cuya
# fecha de desaparición es anterior al inicio de la ventana de reportes de
# este extracto (ver docs/data_dictionary.md). No es un error: son casos de
# larga data incorporados al registro. Se documentan aparte para que no
# distorsionen las estadísticas de tiempo "típico" de resolución reciente.
HISTORIC_CUTOFF_YEARS_BEFORE_WINDOW = 10


def build_quality_flags(cases: pd.DataFrame, report_window_start=None) -> pd.DataFrame:
    q = cases[["case_key"]].copy()

    report_date = cases["report_date"]
    missing_date = cases["missing_date"]
    location_date = cases.get("location_date")
    status = cases.get("status")
    borough = cases.get("borough_missing")

    q["missing_report_date"] = report_date.isna()
    q["missing_event_date"] = missing_date.isna()
    q["missing_borough"] = borough.isna() if borough is not None else True

    if location_date is not None:
        q["missing_location_date"] = location_date.isna()
        q["location_before_report"] = (
            location_date.notna()
            & report_date.notna()
            & (location_date < report_date)
        )
        q["location_before_event"] = (
            location_date.notna()
            & missing_date.notna()
            & (location_date < missing_date)
        )
    else:
        q["missing_location_date"] = True
        q["location_before_report"] = False
        q["location_before_event"] = False

    q["report_before_event"] = (
        report_date.notna()
        & missing_date.notna()
        & (report_date < missing_date)
    )

    if status is not None:
        is_located_text = status.astype("string").str.upper().eq("LOCALIZADO")
        if location_date is not None:
            q["status_located_without_location_date"] = (
                is_located_text & location_date.isna()
            )
            q["status_missing_with_location_date"] = (
                (~is_located_text) & location_date.notna()
            )
        else:
            q["status_located_without_location_date"] = is_located_text
            q["status_missing_with_location_date"] = False
    else:
        q["status_located_without_location_date"] = False
        q["status_missing_with_location_date"] = False

    # Duplicados: mismo contenido en todas las columnas de negocio, distinto
    # identificador. Se calcula sobre las columnas originales relevantes
    # (se excluyen case_key/source_id, que son identificadores).
    compare_cols = [
        c for c in cases.columns
        if c not in ("case_key", "source_id")
    ]
    q["duplicate_content"] = cases[compare_cols].duplicated(keep=False).values

    if report_window_start is not None:
        cutoff = report_window_start - pd.DateOffset(
            years=HISTORIC_CUTOFF_YEARS_BEFORE_WINDOW
        )
        q["historic_missing_date"] = missing_date.notna() & (missing_date < cutoff)
    else:
        q["historic_missing_date"] = False

    q["any_impossible_or_missing_core"] = q[
        ["missing_report_date", "missing_event_date", "location_before_event",
         "report_before_event"]
    ].any(axis=1)

    return q


def quality_summary(flags: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in flags.columns if c != "case_key"]
    total = len(flags)
    records = []
    for col in cols:
        n = int(flags[col].fillna(False).sum())
        records.append({
            "check": col,
            "category": FLAG_CATEGORY.get(col, "DERIVED"),
            "affected_rows": n,
            "pct_rows": round((n / total * 100) if total else 0.0, 2),
        })
    return pd.DataFrame(records)
