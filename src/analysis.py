from __future__ import annotations

import sqlite3
import numpy as np
import pandas as pd

from .config import DB_PATH, OUTPUT_TABLES

# Tamaño mínimo de muestra para reportar comparaciones entre grupos
# (alcaldía, sexo, grupo de edad, año). Con menos casos, una diferencia de
# unos cuantos puntos porcentuales es ruido, no una señal real. Cualquier
# grupo por debajo de este umbral se conserva en el CSV (transparencia)
# pero se marca con below_min_sample_size = 1 para que gráficos y lecturas
# no lo traten como comparable.
MIN_SAMPLE_SIZE = 30


def _query(sql: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


def _flag_small_samples(df: pd.DataFrame, size_col: str = "sample_size") -> pd.DataFrame:
    """Marca grupos por debajo de MIN_SAMPLE_SIZE.

    size_col debe ser el n ANALÍTICO real que usa el KPI como
    denominador (located_with_valid_duration), no el N total del grupo
    (sample_size): un grupo puede tener N total >=30 y aun así calcular
    su porcentaje sobre menos de 30 casos si la mayoría están abiertos
    o excluidos del cálculo de duración (ver docs/METHODOLOGY.md).
    """
    out = df.copy()
    out["below_min_sample_size"] = (out[size_col] < MIN_SAMPLE_SIZE).astype(int)
    return out


def _report_window_months() -> tuple[str, str]:
    """Primer y último mes (YYYY-MM) con al menos un reporte.

    Se usa para marcar, en las tablas de flujo mensual, qué meses caen
    dentro de la ventana real de reportes (2019-06 a 2022-11) y cuáles
    son meses "extra" que solo existen porque hubo una localización
    (location_date) fuera de esa ventana. Ver nota en export_sql_kpis()
    sobre por qué monthly_flow tiene más filas que meses de reporte.
    """
    bounds = _query("""
        SELECT MIN(substr(report_date, 1, 7)) AS min_month,
               MAX(substr(report_date, 1, 7)) AS max_month
        FROM vw_cases
        WHERE report_date IS NOT NULL
    """)
    return bounds.loc[0, "min_month"], bounds.loc[0, "max_month"]


def _flag_report_window(df: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    """Agrega in_report_window: 1 si el mes cae dentro de la ventana real
    de reportes (min/max de report_date), 0 si es un mes que solo existe
    en la tabla por una localización (location_date) fuera de esa
    ventana (backlog histórico anterior al arranque del registro, o una
    localización posterior al último reporte observado).
    """
    min_month, max_month = _report_window_months()
    out = df.copy()
    out["in_report_window"] = (
        (out[month_col] >= min_month) & (out[month_col] <= max_month)
    ).astype(int)
    return out


def export_sql_kpis() -> dict[str, pd.DataFrame]:
    outputs = {
        "kpi_overview": _query("SELECT * FROM vw_kpi_overview"),
        "borough_kpis": _flag_small_samples(
            _query("SELECT * FROM vw_borough_kpis ORDER BY sample_size DESC"),
            size_col="located_with_valid_duration",
        ),
        "sex_kpis": _flag_small_samples(
            _query("SELECT * FROM vw_sex_kpis ORDER BY sample_size DESC"),
            size_col="located_with_valid_duration",
        ),
        "age_group_kpis": _flag_small_samples(
            _query("SELECT * FROM vw_age_group_kpis ORDER BY age_group"),
            size_col="located_with_valid_duration",
        ),
        "year_kpis": _flag_small_samples(
            _query("SELECT * FROM vw_year_kpis ORDER BY report_year"),
            size_col="located_with_valid_duration",
        ),
        "monthly_flow": _flag_report_window(
            _query("SELECT * FROM vw_monthly_flow ORDER BY month")
        ),
        "cohort_resolution": _query(
            "SELECT * FROM vw_report_cohorts ORDER BY report_month"
        ),
    }
    # monthly_flow tiene una fila por cada mes con AL MENOS un reporte O
    # AL MENOS una localización (ver vw_monthly_flow en sql/02_views.sql).
    # Por eso puede tener más filas que meses de reporte: localizaciones
    # de backlog muy antiguo (location_date antes de que arrancara el
    # registro) o una localización un mes después del último reporte
    # generan meses "extra" con reports=0. in_report_window distingue
    # ambos casos sin alterar ninguna cifra existente.
    for name, df in outputs.items():
        df.to_csv(OUTPUT_TABLES / f"{name}.csv", index=False, encoding="utf-8-sig")
    return outputs


def export_time_distribution() -> pd.DataFrame:
    df = _query("""
        SELECT report_to_location_days
        FROM vw_cases
        WHERE valid_for_report_timeline = 1
          AND is_located = 1
          AND report_to_location_days IS NOT NULL
          AND report_to_location_days >= 0
    """)
    if df.empty:
        out = pd.DataFrame([{
            "n_located_with_valid_duration": 0,
            "median_days": np.nan,
            "p75_days": np.nan,
            "p90_days": np.nan,
            "p95_days": np.nan,
        }])
    else:
        s = df["report_to_location_days"]
        out = pd.DataFrame([{
            "n_located_with_valid_duration": int(s.notna().sum()),
            "median_days": float(s.median()),
            "p75_days": float(s.quantile(0.75)),
            "p90_days": float(s.quantile(0.90)),
            "p95_days": float(s.quantile(0.95)),
        }])
    out.to_csv(OUTPUT_TABLES / "time_distribution.csv", index=False, encoding="utf-8-sig")
    return out


def export_reporting_delay_distribution() -> pd.DataFrame:
    """Tiempo entre la DESAPARICIÓN y el REPORTE a la Comisión.

    Se calcula con y sin los casos marcados como historic_missing_date
    (desapariciones de larga data, ver docs/data_dictionary.md), porque
    ese pequeño grupo de outliers (~2.6% de los casos) es tan extremo
    (décadas) que por sí solo dispara el promedio. El promedio "con
    outliers" no es un error de cálculo: es la razón por la que se
    reporta también la mediana y la versión sin outliers.
    """
    df = _query("""
        SELECT event_to_report_days, historic_missing_date
        FROM vw_cases
        WHERE event_to_report_days IS NOT NULL
    """)
    rows = []
    for label, subset in [
        ("all_cases", df["event_to_report_days"]),
        ("excluding_historic_missing_date", df.loc[df["historic_missing_date"] == 0, "event_to_report_days"]),
    ]:
        if subset.empty:
            rows.append({"segment": label, "n": 0, "mean_days": np.nan, "median_days": np.nan,
                         "p75_days": np.nan, "p90_days": np.nan})
        else:
            rows.append({
                "segment": label,
                "n": int(subset.shape[0]),
                "mean_days": round(float(subset.mean()), 1),
                "median_days": round(float(subset.median()), 1),
                "p75_days": round(float(subset.quantile(0.75)), 1),
                "p90_days": round(float(subset.quantile(0.90)), 1),
            })
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_TABLES / "reporting_delay_distribution.csv", index=False, encoding="utf-8-sig")
    return out


def _km_curve(durations_days: pd.Series, observed: pd.Series) -> pd.DataFrame:
    """Kaplan-Meier calculado a mano (sin lifelines) para que sea fácil de
    explicar en una entrevista: en cada tiempo de evento, la probabilidad
    de "seguir sin localizarse" se multiplica por (1 - eventos/en_riesgo).
    Los casos censurados (aún abiertos) solo reducen el grupo "en riesgo";
    nunca cuentan como localización.
    """
    data = pd.DataFrame({
        "t": pd.to_numeric(durations_days, errors="coerce"),
        "event": observed.astype(bool),
    }).dropna(subset=["t"])
    data = data[data["t"] >= 0].sort_values("t")

    if data.empty:
        return pd.DataFrame(columns=["days", "survival_unresolved", "at_risk", "events"])

    event_times = sorted(data.loc[data["event"], "t"].unique())
    survival = 1.0
    rows = [{"days": 0.0, "survival_unresolved": 1.0, "at_risk": len(data), "events": 0}]
    for t in event_times:
        at_risk = int((data["t"] >= t).sum())
        events = int(((data["t"] == t) & data["event"]).sum())
        if at_risk > 0:
            survival *= (1.0 - events / at_risk)
            rows.append({
                "days": float(t), "survival_unresolved": float(survival),
                "at_risk": at_risk, "events": events,
            })
    return pd.DataFrame(rows)


def _survival_at(curve: pd.DataFrame, day: float) -> float:
    if curve.empty:
        return np.nan
    eligible = curve[curve["days"] <= day]
    if eligible.empty:
        return 1.0
    return float(eligible.iloc[-1]["survival_unresolved"])


def export_survival_snapshot() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Supervivencia general (Kaplan-Meier) desde el REPORTE, usando
    vw_survival_input: incluye tanto casos localizados (evento) como
    abiertos (censurados a la fecha máxima observada en el extracto).
    Esta es la estimación correcta de "% localizado a N días" que sí
    considera a los casos aún no localizados (pregunta B). El KPI simple
    de vw_kpi_overview (pregunta A, solo entre localizados) se calcula
    aparte porque responde una pregunta distinta.
    """
    cases = _query("SELECT case_key, duration_days, event_observed FROM vw_survival_input")
    if cases.empty:
        curve = pd.DataFrame(columns=["days", "survival_unresolved", "at_risk", "events"])
        summary = pd.DataFrame(columns=["threshold_days", "estimated_pct_located", "estimated_pct_still_unresolved"])
        curve.to_csv(OUTPUT_TABLES / "survival_curve.csv", index=False)
        summary.to_csv(OUTPUT_TABLES / "survival_kpis.csv", index=False)
        return curve, summary

    curve = _km_curve(cases["duration_days"], cases["event_observed"])
    curve.to_csv(OUTPUT_TABLES / "survival_curve.csv", index=False, encoding="utf-8-sig")

    rows = []
    for day in [1, 3, 7, 30]:
        s = _survival_at(curve, day)
        rows.append({
            "threshold_days": day,
            "estimated_pct_located": round((1 - s) * 100, 2) if pd.notna(s) else np.nan,
            "estimated_pct_still_unresolved": round(s * 100, 2) if pd.notna(s) else np.nan,
            "n_at_risk_total": int(len(cases)),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_TABLES / "survival_kpis.csv", index=False, encoding="utf-8-sig")
    return curve, summary


def export_survival_by_group(group_col: str, min_n: int = MIN_SAMPLE_SIZE) -> pd.DataFrame:
    """Curvas de supervivencia separadas por grupo (sexo, alcaldía, grupo
    de edad). Los grupos con menos de min_n casos en riesgo se excluyen
    para no comparar curvas construidas con muestras diminutas (ver
    docs/METHODOLOGY.md).
    """
    cases = _query(
        f"SELECT {group_col} AS grp, duration_days, event_observed "
        f"FROM vw_survival_input WHERE {group_col} IS NOT NULL"
    )
    if cases.empty:
        return pd.DataFrame(columns=["group", "days", "survival_unresolved"])

    frames = []
    counts = cases["grp"].value_counts()
    for grp, n in counts.items():
        if n < min_n:
            continue
        sub = cases[cases["grp"] == grp]
        curve = _km_curve(sub["duration_days"], sub["event_observed"])
        curve.insert(0, "group", grp)
        curve.insert(1, "sample_size", int(n))
        frames.append(curve)

    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["group", "sample_size", "days", "survival_unresolved", "at_risk", "events"]
    )
    out.to_csv(OUTPUT_TABLES / f"survival_by_{group_col}.csv", index=False, encoding="utf-8-sig")
    return out


def export_pressure_signals() -> pd.DataFrame:
    monthly = _query("""
        SELECT
            m.month,
            m.reports,
            m.localizations,
            m.net_backlog_flow,
            c.pct_matured_reports_located_le_3d
        FROM vw_monthly_flow m
        LEFT JOIN vw_report_cohorts c
          ON m.month = c.report_month
        ORDER BY m.month
    """)
    if monthly.empty:
        monthly.to_csv(OUTPUT_TABLES / "pressure_signals.csv", index=False)
        return monthly

    monthly = _flag_report_window(monthly)

    # monthly_flow trae 6 meses "de relleno" que no son meses reales del
    # programa de reportes (ver §7 de outputs/FINAL_FINDINGS.md): existen
    # solo porque una localización cayó fuera de la ventana de reportes.
    # Si se dejan como reports=0 dentro de la línea de tiempo, contaminan
    # el promedio/desviación móvil de 12 meses de los primeros meses
    # reales de la ventana (2019-11 y 2019-12 quedaban con z-scores
    # inflados por arrastrar 5 "meses fantasma" con 0 reportes). Se
    # enmascaran a NaN para el cálculo de la línea base -- así
    # min_periods exige meses reales de historia, no filas de la tabla.
    reports_in_window = monthly["reports"].where(monthly["in_report_window"] == 1)
    monthly["report_roll12_mean"] = reports_in_window.shift(1).rolling(12, min_periods=6).mean()
    monthly["report_roll12_std"] = reports_in_window.shift(1).rolling(12, min_periods=6).std(ddof=0)
    monthly["report_z"] = (
        (monthly["reports"] - monthly["report_roll12_mean"])
        / monthly["report_roll12_std"].replace(0, np.nan)
    )
    # pct_matured_reports_located_le_3d ya viene NULL para los meses fuera
    # de ventana (vw_report_cohorts solo agrupa por report_date, que no
    # existe en esos meses de relleno), así que resolution3d_roll6 ya
    # respeta min_periods sobre meses reales sin necesidad de enmascarar.
    rate = monthly["pct_matured_reports_located_le_3d"]
    monthly["resolution3d_roll6"] = rate.shift(1).rolling(6, min_periods=3).mean()
    monthly["pressure_signal"] = (
        (monthly["in_report_window"] == 1)
        & (monthly["report_z"] >= 2.0)
        & rate.notna()
        & monthly["resolution3d_roll6"].notna()
        & (rate < monthly["resolution3d_roll6"])
    ).astype(int)

    monthly.to_csv(OUTPUT_TABLES / "pressure_signals.csv", index=False, encoding="utf-8-sig")
    return monthly


def export_quality_detail() -> pd.DataFrame:
    """Muestra (no exhaustiva) de casos con problemas de calidad, para
    documentar con ejemplos reales en docs/ sin publicar el registro
    completo caso-a-caso."""
    df = _query("""
        SELECT
            case_key, report_date, missing_date, location_date, status,
            borough_missing,
            location_before_report, location_before_event, report_before_event,
            status_located_without_location_date, status_missing_with_location_date,
            duplicate_content, historic_missing_date
        FROM vw_cases
        WHERE location_before_report = 1
           OR location_before_event = 1
           OR report_before_event = 1
           OR status_located_without_location_date = 1
           OR duplicate_content = 1
           OR historic_missing_date = 1
        ORDER BY case_key
        LIMIT 200
    """)
    df.to_csv(OUTPUT_TABLES / "location_before_report_sample.csv", index=False, encoding="utf-8-sig")
    return df
