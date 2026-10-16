from __future__ import annotations

"""Ampliación de 72 HORAS: desenlaces CON VIDA / SIN VIDA.

Módulo nuevo y separado de analysis.py a propósito: no modifica ninguna
función ni resultado del análisis general de velocidad de localización.
Todo lo de aquí es adicional.

ADVERTENCIA METODOLÓGICA (repetida también en docs/METHODOLOGY.md y
outputs/FINAL_FINDINGS.md porque es fácil de olvidar al leer una cifra
suelta): location_date es la fecha en que el caso se cerró
administrativamente como localizado. NO es necesariamente la fecha de
fallecimiento en los casos SIN VIDA -- la persona pudo haber fallecido
antes de que el caso se cerrara. Nada en este módulo debe usarse para
afirmar cuándo murió alguien, ni que una búsqueda más rápida habría
evitado un desenlace SIN VIDA. Lo que se mide es la asociación entre el
tiempo hasta el cierre del caso y el desenlace registrado al cierre --
nunca causalidad, nunca momento del deceso.
"""

import sqlite3
import numpy as np
import pandas as pd

from .config import DB_PATH, OUTPUT_TABLES, EXTRACT_CUTOFF_DATE
from .analysis import MIN_SAMPLE_SIZE, _query as _analysis_query  # reutiliza el mismo umbral

INTERVAL_ORDER = ["1_≤1 día", "2_>1-3 días", "3_>3-7 días", "4_>7-30 días", "5_>30 días"]
INTERVAL_LABELS = {
    "1_≤1 día": "≤1 día",
    "2_>1-3 días": ">1-3 días",
    "3_>3-7 días": ">3-7 días",
    "4_>7-30 días": ">7-30 días",
    "5_>30 días": ">30 días",
}

# NOTA HISTÓRICA (ver CHANGELOG.md): este módulo usaba antes
# lifelines.AalenJohansenFitter con una semilla fija (_AJ_SEED = 42) para
# hacer reproducible el jitter aleatorio con el que esa librería resuelve
# empates de tiempo. Se detectó que ese jitter no solo afectaba la
# reproducibilidad -- introducía un sesgo real al desplazar casos
# empatados justo en un umbral entero (p. ej. día 1) hacia uno u otro
# lado. Se reemplazó por `_competing_risk_cif`, un cálculo exacto y
# determinista que no requiere semilla. La constante de semilla ya no
# existe -- si algún código externo a este proyecto la importaba, debe
# eliminarse esa dependencia.


def _query(sql: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza de Wilson para una proporción k/n.

    Se usa Wilson en vez del intervalo normal simple porque es más
    confiable con N chicas y proporciones cercanas a 0 (exactamente la
    situación de SIN VIDA, que es un evento minoritario incluso en los
    grupos con más casos).
    """
    if n == 0:
        return (np.nan, np.nan)
    phat = k / n
    denom = 1 + z ** 2 / n
    center = phat + z ** 2 / (2 * n)
    margin = z * np.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2))
    lo, hi = (center - margin) / denom, (center + margin) / denom
    # Clamp: con k=0 o k=n, la aritmética de punto flotante puede dar un
    # residuo como -1e-17 en vez de exactamente 0 (o 1+1e-17). Una
    # proporción nunca es negativa ni mayor a 1.
    return (max(0.0, lo), min(1.0, hi))


def export_outcome_audit() -> pd.DataFrame:
    """Punto 1: audita location_condition contra el total de localizados.

    Verificado contra el archivo crudo (no solo contra vw_cases): 0 casos
    con estatus DESAPARECIDO tienen location_condition no nulo -- no hay
    fuga de la condición hacia casos abiertos. Los "faltantes" son
    exclusivamente dentro de los 1,777 localizados.
    """
    df = _query("SELECT * FROM vw_outcome_overview")
    row = df.iloc[0]
    checks = pd.DataFrame([
        {"chequeo": "total_localizados", "valor": int(row["total_localizados"])},
        {"chequeo": "con_vida", "valor": int(row["con_vida"])},
        {"chequeo": "sin_vida", "valor": int(row["sin_vida"])},
        {"chequeo": "condicion_desconocida", "valor": int(row["condicion_desconocida"])},
        {"chequeo": "suma_con_vida_sin_vida_desconocida_debe_igualar_total_localizados",
         "valor": int(row["con_vida"] + row["sin_vida"] + row["condicion_desconocida"])},
        {"chequeo": "condicion_conocida_pero_sin_fecha_de_localizacion_usable",
         "valor": int(row["condicion_conocida_sin_fecha"])},
        {"chequeo": "fecha_de_localizacion_usable_pero_condicion_desconocida",
         "valor": int(row["fecha_conocida_sin_condicion"])},
        {"chequeo": "condicion_conocida_y_con_duracion_reporte_valida (n_analitico usado en interval/CIF)",
         "valor": int(row["condicion_conocida_con_duracion_valida"])},
    ])
    checks.to_csv(OUTPUT_TABLES / "outcome_audit.csv", index=False, encoding="utf-8-sig")
    return checks


def export_outcome_intervals() -> dict[str, pd.DataFrame]:
    """Punto 2: desenlace por intervalo de tiempo, en los dos relojes."""
    outputs = {}
    for clock, view in [("report_clock", "vw_outcome_interval_report"),
                         ("missing_clock", "vw_outcome_interval_missing")]:
        raw = _query(f"SELECT * FROM {view}")
        pivot = raw.pivot_table(index="interval_bucket", columns="location_condition",
                                 values="n", fill_value=0, aggfunc="sum")
        pivot = pivot.reindex(INTERVAL_ORDER, fill_value=0)
        for col in ["CON VIDA", "SIN VIDA", "DESCONOCIDA"]:
            if col not in pivot.columns:
                pivot[col] = 0
        pivot = pivot[["CON VIDA", "SIN VIDA", "DESCONOCIDA"]]
        pivot["total"] = pivot.sum(axis=1)
        # % de columna: dentro de cada desenlace, cómo se reparte en el tiempo.
        for col in ["CON VIDA", "SIN VIDA", "DESCONOCIDA"]:
            total_col = pivot[col].sum()
            pivot[f"pct_{col.replace(' ', '_')}"] = (
                100 * pivot[col] / total_col if total_col else np.nan
            ).round(2)
        # % de fila: dentro de cada intervalo, qué fracción terminó SIN VIDA.
        pivot["pct_sin_vida_del_intervalo"] = (
            100 * pivot["SIN VIDA"] / pivot["total"]
        ).round(2)
        pivot.index = [INTERVAL_LABELS[i] for i in pivot.index]
        pivot.index.name = "intervalo"
        pivot = pivot.reset_index()
        pivot.to_csv(OUTPUT_TABLES / f"outcome_intervals_{clock}.csv", index=False, encoding="utf-8-sig")
        outputs[clock] = pivot

    # Exclusiones: localizados que NO entran en cada reloj, por condición.
    excl_rows = []
    for clock, valid_col, dur_col in [
        ("report_clock", "valid_for_report_timeline", "report_to_location_days"),
        ("missing_clock", "valid_for_missing_timeline", "missing_to_location_days"),
    ]:
        cases = _analysis_query(f"""
            SELECT location_condition, {valid_col} AS valido
            FROM vw_cases WHERE is_located = 1
        """)
        cases["cond"] = cases["location_condition"].fillna("DESCONOCIDA")
        excl = cases[cases["valido"] == 0]["cond"].value_counts()
        for cond, n in excl.items():
            excl_rows.append({"reloj": clock, "location_condition": cond, "n_excluido": int(n)})
    exclusions = pd.DataFrame(excl_rows)
    exclusions.to_csv(OUTPUT_TABLES / "outcome_intervals_exclusions.csv", index=False, encoding="utf-8-sig")
    outputs["exclusions"] = exclusions
    return outputs


def _group_outcome_table(view: str, group_col: str) -> pd.DataFrame:
    df = _query(f"SELECT * FROM {view}")
    rows = []
    for _, r in df.iterrows():
        n = int(r["n_analitico"])
        k = int(r["sin_vida_n"])
        pct = round(100 * k / n, 2) if n else np.nan
        lo, hi = wilson_ci(k, n)
        rows.append({
            group_col: r[group_col],
            "n_analitico": n,
            "sin_vida_n": k,
            "pct_sin_vida": pct,
            "ci95_low": round(lo * 100, 2) if pd.notna(lo) else np.nan,
            "ci95_high": round(hi * 100, 2) if pd.notna(hi) else np.nan,
            "below_min_sample_size": int(n < MIN_SAMPLE_SIZE),
        })
    return pd.DataFrame(rows).sort_values("pct_sin_vida", ascending=False)


def export_outcome_group_kpis() -> dict[str, pd.DataFrame]:
    """Punto 3: desenlace por sexo, edad y alcaldía, con N e incertidumbre.

    n_analitico aquí = localizados con location_condition conocida (no
    exige duración válida; ver outputs/FINAL_FINDINGS.md §11 para la
    justificación). below_min_sample_size usa el mismo umbral (30) que
    el resto del proyecto, aplicado sobre este n_analitico -- igual
    criterio que ya se corrigió para el análisis general de velocidad.
    """
    outputs = {
        "sex": _group_outcome_table("vw_outcome_sex_kpis", "sex"),
        "age_group": _group_outcome_table("vw_outcome_age_group_kpis", "age_group"),
        "borough": _group_outcome_table("vw_outcome_borough_kpis", "borough_missing"),
    }
    for name, df in outputs.items():
        df.to_csv(OUTPUT_TABLES / f"outcome_by_{name}.csv", index=False, encoding="utf-8-sig")
    return outputs


def _competing_risk_cif(durations: pd.Series, event_types: pd.Series) -> pd.DataFrame:
    """Función de incidencia acumulada (Aalen-Johansen) para riesgos
    competitivos, calculada exactamente sobre los días originales (enteros),
    respetando empates -- SIN jitter aleatorio.

    CORRECCIÓN (ver CHANGELOG): la versión anterior usaba
    lifelines.AalenJohansenFitter, que resuelve tiempos empatados con un
    jitter aleatorio continuo (lifelines emite una advertencia explícita
    sobre esto). Con datos en días enteros y empates masivos -- cientos de
    casos localizados el mismo día 0 o día 1 -- ese jitter desplaza una
    fracción sustancial de esos casos a un lado u otro de un umbral entero
    como "≤1 día". No es ruido de redondeo: es un sesgo real y
    verificable. Ejemplo medido: a ≤1 día, CON VIDA daba 20.55% con jitter
    vs. 25.02% con el cálculo exacto -- una diferencia de ~4.5 puntos
    causada enteramente por el jitter, no por los datos.

    Fórmula usada (Kalbfleisch & Prentice 1980 -- el estimador estándar de
    incidencia acumulada, que agrega los empates en vez de romperlos):

        S(t-)     = supervivencia general ("cualquier evento", Kaplan-Meier)
                    justo antes de t
        CIF_k(t)  = CIF_k(t-) + S(t-) * d_k(t) / n(t)

    donde d_k(t) es el número de eventos de tipo k exactamente en t y n(t)
    el número en riesgo justo antes de t. Esta fórmula es determinista: no
    depende de ninguna semilla aleatoria.

    CORRECCIÓN ADICIONAL (encontrada durante la auditoría de la fecha de
    corte -- ver CHANGELOG.md): S(t-) debe actualizarse dividiendo SOLO
    entre los EVENTOS (de cualquier tipo) ocurridos en t, nunca sumando
    también las censuras de ese mismo t -- la censura reduce el
    denominador n(t) para el SIGUIENTE paso (porque ya no aparece en
    `duration >= t_siguiente`), pero no debe restarse otra vez en la
    actualización de la supervivencia, o se cuenta dos veces. La versión
    anterior de esta función sí sumaba la censura ahí -- un error inerte
    mientras el corte de censura (`EXTRACT_CUTOFF_DATE`) empujaba a los
    casos abiertos lejos de los días tempranos donde ocurren los eventos
    reales, así que nunca había empates entre censura y evento y el error
    no se manifestaba (verificado: con el corte antiguo, sin empates,
    ambas fórmulas coinciden). Al corregir el corte a una fecha más
    temprana y correcta, empezaron a aparecer casos abiertos censurados
    en los mismos días que eventos reales -- eso expuso el error: sin
    esta corrección, la función daba una cifra distinta de la del
    Kaplan-Meier de "cualquier evento" calculado independientemente con
    `lifelines.KaplanMeierFitter` (verificado con un ejemplo mínimo:
    duraciones [1,1,2,3], eventos [evento,censurado empatado en 1,evento,
    censurado] -- la fórmula incorrecta daba 0.5, lifelines daba 0.625;
    con esta corrección, ambas dan 0.625).

    Propiedad de verificación (usada en tests/test_outcomes.py): la suma
    de los CIF de TODOS los tipos de evento en cualquier día debe
    reproducir exactamente el Kaplan-Meier de "cualquier evento" sobre la
    misma población -- es una identidad matemática, no una coincidencia.
    """
    df = pd.DataFrame({
        "duration": durations.astype(int).to_numpy(),
        "event": event_types.to_numpy(),
    })
    event_labels = sorted(int(e) for e in df["event"].unique() if e != 0)
    times = np.sort(df["duration"].unique())
    s_prev = 1.0
    cif = {e: 0.0 for e in event_labels}
    rows = []
    for t in times:
        at_t = df[df["duration"] == t]
        n_i = int((df["duration"] >= t).sum())
        d_by_type = {e: int((at_t["event"] == e).sum()) for e in event_labels}
        for e in event_labels:
            cif[e] = cif[e] + s_prev * (d_by_type[e] / n_i)
        # Solo los EVENTOS (no la censura) reducen la supervivencia aquí.
        # La censura ya se refleja automáticamente en n_i del siguiente
        # paso, porque esos casos dejan de cumplir `duration >= t`.
        s_prev = s_prev * (1 - sum(d_by_type.values()) / n_i)
        rows.append({"days": int(t), "n_en_riesgo": n_i, **{f"cif_{e}": cif[e] for e in event_labels}})
    return pd.DataFrame(rows)


def export_outcome_competing_risk() -> dict[str, pd.DataFrame]:
    """Punto 4: riesgos competitivos CON VIDA / SIN VIDA (Aalen-Johansen).

    Por qué NO se reutiliza el Kaplan-Meier general (vw_survival_input):
    ese KM trata "estar localizado" como un solo evento. Si en cambio se
    quisiera medir el desenlace SIN VIDA con un KM simple (evento=SIN
    VIDA, censurando todo lo demás -- abiertos Y localizados CON VIDA),
    el resultado está sesgado hacia arriba: ignora que los casos CON VIDA
    "salen" de la población en riesgo antes de tiempo por una razón
    distinta a la censura. El estimador correcto para dos o más
    desenlaces que compiten por el mismo caso es la función de incidencia
    acumulada de Aalen-Johansen, calculada aquí con `_competing_risk_cif`
    (cálculo exacto, sin jitter -- ver esa función para el porqué). Este
    módulo exporta AMBOS cálculos -- el ingenuo (mal usado) y el correcto
    -- para dejar documentada la magnitud real del sesgo, no para usar el
    ingenuo en ningún hallazgo.
    """
    from lifelines import KaplanMeierFitter

    pop = _query("SELECT * FROM vw_outcome_competing_risk_input")
    # CORREGIDO (ver CHANGELOG.md y src/config.py::EXTRACT_CUTOFF_DATE):
    # antes se inferÍa como MAX(report_date, location_date), que el caso
    # ID 1138 (location_date = 2022-12-15, muy fuera de línea) desplazaba
    # un mes completo. Se usa ahora la misma fecha de corte documentada
    # y explícita que usan las vistas SQL (vw_survival_input,
    # vw_report_cohorts), para que el corte sea consistente en todo el
    # proyecto en vez de recalculado por separado en cada lugar.
    cutoff = pd.to_datetime(EXTRACT_CUTOFF_DATE)

    # CORREGIDO (auditoría de consistencia del corte -- ver
    # docs/METHODOLOGY.md §7.1): un location_date POSTERIOR al corte no
    # puede tratarse como un evento observado -- esa información no
    # existiría todavía "al momento del corte". Antes de esta corrección,
    # `event_type` (calculado en la vista SQL sin conocer el corte) se
    # usaba tal cual, así que el caso ID 1138 (location_date = 2022-12-15,
    # posterior al corte 2022-11-15) entraba como evento CON VIDA
    # observado a los 464 días. Se re-censura aquí, en Python, porque el
    # corte es la constante EXTRACT_CUTOFF_DATE (no un literal SQL
    # adicional que mantener sincronizado en un tercer lugar): mismo
    # criterio que ya aplica sql/02_views.sql::vw_survival_input.
    # Verificado: es el único caso del extracto con esta condición.
    location_date = pd.to_datetime(pop["location_date"])
    observed_after_cutoff = (pop["event_type"] != 0) & (location_date > cutoff)
    n_recensurados = int(observed_after_cutoff.sum())
    pop.loc[observed_after_cutoff, "event_type"] = 0

    pop["duration"] = np.where(
        pop["event_type"] != 0,
        pop["report_to_location_days"],
        (cutoff - pd.to_datetime(pop["report_date"])).dt.days,
    )

    n_total = len(pop)
    n_con_vida = int((pop["event_type"] == 1).sum())
    n_sin_vida = int((pop["event_type"] == 2).sum())
    n_desconocida = int((pop["event_type"] == 3).sum())
    n_censurado = int((pop["event_type"] == 0).sum())

    cif_table = _competing_risk_cif(pop["duration"], pop["event_type"])

    curves = {}
    summary_rows = []
    for et, label in [(1, "CON VIDA"), (2, "SIN VIDA")]:
        col = f"cif_{et}"
        curve = cif_table[["days", col]].rename(columns={col: "cif"}).copy()
        curves[label] = curve
        curve.to_csv(
            OUTPUT_TABLES / f"outcome_cif_curve_{label.lower().replace(' ', '_')}.csv",
            index=False, encoding="utf-8-sig",
        )
        for day in [1, 3, 7, 30]:
            sub = cif_table[cif_table["days"] <= day]
            val = float(sub[col].iloc[-1]) if len(sub) else 0.0
            summary_rows.append({"threshold_days": day, "desenlace": label,
                                  "cif_pct_correcto_aalen_johansen": round(val * 100, 5)})

    # DESCONOCIDA (event_type=3) ya se calculaba dentro de _competing_risk_cif
    # (es un tercer desenlace que compite) pero no se exportaba -- solo se
    # usaba internamente para que la identidad CIF-suma-igual-a-KM-general
    # cerrara. Se expone aquí (sin comparación "ingenuo vs. correcto": no
    # tiene sentido para este desenlace, que no es el foco del proyecto)
    # para que outputs/FINAL_FINDINGS.md pueda reportar por separado
    # CON VIDA + SIN VIDA + DESCONOCIDA + S(t) = 100%, en vez de mezclar
    # DESCONOCIDA dentro de "aún sin desenlace" -- son cosas distintas:
    # DESCONOCIDA ya tuvo un evento de localización, solo que sin
    # condición capturada; "aún sin desenlace" (S(t)) son casos que
    # siguen sin ningún evento de localización.
    if "cif_3" in cif_table.columns:
        curve3 = cif_table[["days", "cif_3"]].rename(columns={"cif_3": "cif"}).copy()
        curves["DESCONOCIDA"] = curve3
        curve3.to_csv(
            OUTPUT_TABLES / "outcome_cif_curve_desconocida.csv",
            index=False, encoding="utf-8-sig",
        )
        for day in [1, 3, 7, 30]:
            sub = cif_table[cif_table["days"] <= day]
            val = float(sub["cif_3"].iloc[-1]) if len(sub) else 0.0
            summary_rows.append({"threshold_days": day, "desenlace": "DESCONOCIDA",
                                  "cif_pct_correcto_aalen_johansen": round(val * 100, 5)})

    # Comparación con el método ingenuo (documentada, no usada como hallazgo).
    # El KM estándar (un solo evento, sin riesgos competitivos) SÍ maneja
    # empates correctamente de forma nativa -- no necesita jitter, así que
    # esta parte del cálculo no cambia con la corrección de este archivo.
    # No se calcula para DESCONOCIDA (no es un hallazgo del proyecto,
    # existe solo para que la identidad de suma cierre).
    naive_rows = []
    for et, label in [(1, "CON VIDA"), (2, "SIN VIDA")]:
        kmf = KaplanMeierFitter()
        naive_event = (pop["event_type"] == et).astype(int)
        kmf.fit(pop["duration"], naive_event)
        for day in [1, 3, 7, 30]:
            s = kmf.survival_function_at_times(day)
            naive_pct = round((1 - float(s.iloc[0])) * 100, 5)
            naive_rows.append({"threshold_days": day, "desenlace": label,
                                "pct_ingenuo_km_mal_usado": naive_pct})

    summary = pd.DataFrame(summary_rows).merge(
        pd.DataFrame(naive_rows), on=["threshold_days", "desenlace"], how="left"
    )
    summary["sobreestimacion_relativa_pct"] = round(
        100 * (summary["pct_ingenuo_km_mal_usado"] / summary["cif_pct_correcto_aalen_johansen"] - 1), 2
    )
    summary["n_en_riesgo_total"] = n_total
    summary["n_con_vida"] = n_con_vida
    summary["n_sin_vida"] = n_sin_vida
    summary["n_condicion_desconocida"] = n_desconocida
    summary["n_censurado_abierto"] = n_censurado
    summary["n_recensurado_por_corte"] = n_recensurados
    summary.to_csv(OUTPUT_TABLES / "outcome_cif_summary.csv", index=False, encoding="utf-8-sig")

    return {"curves": curves, "summary": summary, "cif_table": cif_table}
