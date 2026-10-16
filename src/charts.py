from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt

from .config import OUTPUT_TABLES, OUTPUT_CHARTS
from .analysis import MIN_SAMPLE_SIZE

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _read(name: str) -> pd.DataFrame:
    path = OUTPUT_TABLES / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _chart_monthly_flow() -> None:
    """Pregunta: ¿cómo se comparan reportes nuevos vs. localizaciones mes
    a mes? Responde flujo de entrada vs. resolución, no el stock abierto."""
    monthly = _read("monthly_flow.csv")
    if monthly.empty or "month" not in monthly:
        return
    monthly["month"] = pd.to_datetime(monthly["month"], errors="coerce")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(monthly["month"], monthly["reports"], label="Reportes nuevos", linewidth=2)
    ax.plot(monthly["month"], monthly["localizations"], label="Localizaciones", linewidth=2)
    ax.set_title("Flujo mensual: reportes nuevos vs. localizaciones")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Casos")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "01_monthly_flow.png", dpi=180)
    plt.close(fig)


def _chart_borough_72h() -> None:
    """Pregunta: ¿en qué alcaldías la localización dentro de 3 días
    (≈72h) es menos frecuente, entre los casos ya localizados? Alcaldías
    con muestra menor al mínimo se excluyen del gráfico (se conservan en
    el CSV) para no sugerir un ranking engañoso."""
    borough = _read("borough_kpis.csv")
    needed = {"borough_missing", "pct_located_le_3d_among_located", "below_min_sample_size"}
    if borough.empty or not needed.issubset(borough.columns):
        return
    plot = borough[borough["below_min_sample_size"] == 0].dropna(
        subset=["borough_missing", "pct_located_le_3d_among_located"]
    ).sort_values("pct_located_le_3d_among_located")
    if plot.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(plot["borough_missing"], plot["pct_located_le_3d_among_located"], color="#3B6E8F")
    ax.set_title(f"% localizado en ≤3 días desde el reporte, por alcaldía\n(entre casos ya localizados; N≥{MIN_SAMPLE_SIZE})")
    ax.set_xlabel("% localizado en ≤3 días")
    ax.set_ylabel("Alcaldía de la desaparición")
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "02_borough_72h.png", dpi=180)
    plt.close(fig)


def _chart_survival_curve() -> None:
    """Pregunta: considerando también los casos aún abiertos, ¿qué
    probabilidad hay de seguir sin localización a N días del reporte?
    Esta es la versión honesta (con censura) de la pregunta 72 horas."""
    surv = _read("survival_curve.csv")
    if surv.empty or not {"days", "survival_unresolved"}.issubset(surv.columns):
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.step(surv["days"], surv["survival_unresolved"], where="post", color="#B0413E", linewidth=2)
    for day in (1, 3, 7, 30):
        ax.axvline(day, color="grey", linestyle=":", linewidth=1)
    ax.set_xlim(left=0, right=min(90, surv["days"].max() if len(surv) else 90))
    ax.set_ylim(0, 1.02)
    ax.set_title("Curva de Kaplan-Meier: probabilidad de seguir sin localización\n(incluye casos abiertos como censura)")
    ax.set_xlabel("Días desde el reporte")
    ax.set_ylabel("P(sin localización)")
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "03_survival_curve.png", dpi=180)
    plt.close(fig)


def _chart_cohort_72h_evolution() -> None:
    """Pregunta: ¿mejoró o empeoró con el tiempo la velocidad de
    localización? Compara, cohorte de reporte por cohorte de reporte
    (mes de reporte), qué % ya estaba localizado dentro de 3 días, SOLO
    entre cohortes ya maduras (>=3 días de antigüedad al corte)."""
    cohorts = _read("cohort_resolution.csv")
    needed = {"report_month", "pct_matured_reports_located_le_3d", "matured_3d_denominator"}
    if cohorts.empty or not needed.issubset(cohorts.columns):
        return
    plot = cohorts[cohorts["matured_3d_denominator"] >= MIN_SAMPLE_SIZE].copy()
    if plot.empty:
        return
    plot["report_month"] = pd.to_datetime(plot["report_month"], errors="coerce")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(plot["report_month"], plot["pct_matured_reports_located_le_3d"],
            marker="o", markersize=3, color="#2E7D5B")
    ax.set_title(f"Evolución mensual: % de reportes localizados en ≤3 días\n(cohortes maduras, N≥{MIN_SAMPLE_SIZE})")
    ax.set_xlabel("Mes de reporte")
    ax.set_ylabel("% localizado en ≤3 días")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "04_cohort_72h_evolution.png", dpi=180)
    plt.close(fig)


def _chart_time_distribution() -> None:
    """Pregunta: entre los casos localizados con duración válida, ¿cómo
    se distribuye el tiempo hasta la localización? Un histograma dice
    más que un solo promedio (que además es sensible a outliers)."""
    from .config import DB_PATH
    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """SELECT report_to_location_days FROM vw_cases
               WHERE is_located = 1 AND valid_for_report_timeline = 1
                 AND report_to_location_days IS NOT NULL""",
            conn,
        )
    if df.empty:
        return
    capped = df["report_to_location_days"].clip(upper=60)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(capped, bins=30, color="#6A5ACD", edgecolor="white")
    ax.axvline(3, color="black", linestyle="--", linewidth=1, label="72 horas")
    ax.set_title("Distribución del tiempo reporte→localización\n(entre casos localizados; recortado a 60 días para legibilidad)")
    ax.set_xlabel("Días desde el reporte")
    ax.set_ylabel("Número de casos")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "05_time_distribution.png", dpi=180)
    plt.close(fig)


def _chart_data_quality() -> None:
    """Pregunta: ¿qué tan grande es cada problema de calidad, y de qué
    tipo es (falta de dato, orden imposible, ambiguo, inconsistencia de
    estatus, duplicado, outlier)? Ordenado por categoría para dejar claro
    que no todos los flags significan lo mismo."""
    q = _read("data_quality_summary.csv")
    if q.empty or "check" not in q.columns:
        return
    q = q[q["check"] != "any_impossible_or_missing_core"].sort_values(["category", "affected_rows"])
    colors = {
        "MISSING": "#9AA5B1", "AMBIGUOUS": "#E8A33D", "IMPOSSIBLE": "#B0413E",
        "MISMATCH": "#6A5ACD", "DUPLICATE": "#3B6E8F", "OUTLIER": "#2E7D5B",
    }
    bar_colors = [colors.get(c, "#999999") for c in q["category"]]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(q["check"], q["pct_rows"], color=bar_colors)
    ax.set_title("Casos afectados por cada regla de calidad (% del total)")
    ax.set_xlabel("% de registros")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax.legend(handles, colors.keys(), title="Categoría", loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "06_data_quality.png", dpi=180)
    plt.close(fig)


def make_charts() -> None:
    _chart_monthly_flow()
    _chart_borough_72h()
    _chart_survival_curve()
    _chart_cohort_72h_evolution()
    _chart_time_distribution()
    _chart_data_quality()


# ===========================================================================
# AMPLIACIÓN: gráficos de desenlaces CON VIDA / SIN VIDA. Funciones nuevas,
# no tocan ninguna de las anteriores. Ver src/outcomes.py para los datos.
# ===========================================================================

def _chart_outcome_intervals() -> None:
    """Pregunta: ¿en qué ventana de tiempo (reloj reporte->localización) se
    concentran los desenlaces CON VIDA y SIN VIDA? Barras agrupadas, no
    apiladas, para no sugerir visualmente que un desenlace "se resta" del
    otro dentro del mismo intervalo (son subconjuntos distintos, no partes
    de un total que compiten en el eje X)."""
    df = _read("outcome_intervals_report_clock.csv")
    if df.empty or "intervalo" not in df.columns:
        return
    import numpy as np
    x = np.arange(len(df))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width / 2, df["CON VIDA"], width, label="CON VIDA", color="#2E7D5B")
    ax.bar(x + width / 2, df["SIN VIDA"], width, label="SIN VIDA", color="#B0413E")
    ax.set_xticks(x)
    ax.set_xticklabels(df["intervalo"])
    ax.set_title("Desenlace por intervalo de tiempo desde el reporte\n(entre localizados con duración válida)")
    ax.set_xlabel("Días desde el reporte hasta el cierre del caso")
    ax.set_ylabel("Casos")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "07_outcome_intervals.png", dpi=180)
    plt.close(fig)


def _chart_outcome_cif() -> None:
    """Pregunta: de TODOS los reportes (incluyendo los aún abiertos), ¿qué
    fracción había terminado CON VIDA vs. SIN VIDA a cada día, según el
    estimador correcto de riesgos competitivos (Aalen-Johansen)? El
    remanente hasta 100% es "aún sin desenlace registrado" (abierto o
    condición desconocida) -- se dibuja como área para que se vea que las
    tres franjas suman el total en riesgo, no que compiten por el mismo
    100% de manera engañosa."""
    con_vida = _read("outcome_cif_curve_con_vida.csv")
    sin_vida = _read("outcome_cif_curve_sin_vida.csv")
    if con_vida.empty or sin_vida.empty:
        return
    merged = pd.merge(con_vida, sin_vida, on="days", how="outer", suffixes=("_con_vida", "_sin_vida"))
    merged = merged.sort_values("days").ffill().fillna(0)
    merged["resto"] = 1 - merged["cif_con_vida"] - merged["cif_sin_vida"]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.stackplot(
        merged["days"],
        merged["cif_sin_vida"] * 100,
        merged["cif_con_vida"] * 100,
        merged["resto"] * 100,
        labels=["SIN VIDA", "CON VIDA", "Aún sin desenlace (abierto / desconocido)"],
        colors=["#B0413E", "#2E7D5B", "#D8DCE1"],
    )
    ax.set_xlim(0, 90)
    ax.set_title("Incidencia acumulada por desenlace desde el reporte\n(riesgos competitivos, Aalen-Johansen — primeros 90 días)")
    ax.set_xlabel("Días desde el reporte")
    ax.set_ylabel("% del total de reportes en riesgo")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "08_outcome_cif.png", dpi=180)
    plt.close(fig)


def _chart_outcome_naive_vs_correct() -> None:
    """Punto pedagógico explícito: cuánto sobreestima el método ingenuo
    (Kaplan-Meier tratando el otro desenlace como censura) frente al
    correcto (Aalen-Johansen), para el desenlace SIN VIDA. No es un
    hallazgo sustantivo del proyecto -- es evidencia de por qué se usó
    el método correcto y no el más simple."""
    df = _read("outcome_cif_summary.csv")
    if df.empty:
        return
    sub = df[df["desenlace"] == "SIN VIDA"].sort_values("threshold_days")
    if sub.empty:
        return
    import numpy as np
    x = np.arange(len(sub))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.bar(x - width / 2, sub["pct_ingenuo_km_mal_usado"], width,
           label="Ingenuo (KM mal usado)", color="#B0413E", alpha=0.55)
    ax.bar(x + width / 2, sub["cif_pct_correcto_aalen_johansen"], width,
           label="Correcto (Aalen-Johansen)", color="#2E7D5B")
    ax.set_xticks(x)
    ax.set_xticklabels([f"≤{d}d" for d in sub["threshold_days"]])
    ax.set_title("SIN VIDA: método ingenuo vs. correcto\n(el ingenuo sobreestima al ignorar el riesgo competitivo)")
    ax.set_ylabel("% estimado")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_CHARTS / "09_outcome_naive_vs_correct.png", dpi=180)
    plt.close(fig)


def make_outcome_charts() -> None:
    _chart_outcome_intervals()
    _chart_outcome_cif()
    _chart_outcome_naive_vs_correct()
