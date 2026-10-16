"""Pruebas de la ampliación de desenlaces CON VIDA / SIN VIDA.

Archivo nuevo y separado de tests/test_import_logic.py a propósito: no
modifica ni depende de los 11 tests existentes. Se ejecuta junto con
ellos vía `pytest -q`.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.outcomes import wilson_ci, _competing_risk_cif


# ---------------------------------------------------------------------
# wilson_ci: valores puros, sin depender de datos ni de la base.
# ---------------------------------------------------------------------

def test_wilson_ci_known_value():
    # k=10, n=100 -> proporción 10%; el CI de Wilson debe contener 0.10
    # y ser razonablemente angosto (referencia: ~[5.5%, 17.4%]).
    lo, hi = wilson_ci(10, 100)
    assert lo < 0.10 < hi
    assert 0.05 < lo < 0.07
    assert 0.16 < hi < 0.19


def test_wilson_ci_zero_events():
    lo, hi = wilson_ci(0, 30)
    assert lo == 0.0
    assert hi > 0.0  # el límite superior no es cero aunque no se haya observado el evento


def test_wilson_ci_n_zero_returns_nan():
    lo, hi = wilson_ci(0, 0)
    assert lo != lo  # NaN != NaN
    assert hi != hi


def test_wilson_ci_narrows_with_larger_n():
    lo_small, hi_small = wilson_ci(10, 50)
    lo_big, hi_big = wilson_ci(100, 500)
    # misma proporción (20%), pero N mayor -> intervalo más angosto
    assert (hi_big - lo_big) < (hi_small - lo_small)


# ---------------------------------------------------------------------
# _competing_risk_cif: pruebas puras con datos sintéticos, sin depender
# de data/raw/ ni de la base -- corrigen el bug real encontrado (jitter
# de lifelines.AalenJohansenFitter desplazando empates fuera del umbral
# de día entero). Referencia de valores calculados a mano en CHANGELOG.md.
# ---------------------------------------------------------------------

def _synthetic_population():
    """10 casos con empates exactamente en los días 1, 3, 7 y 30 -- los
    mismos días que usa el proyecto como umbrales (≤1, ≤3, ≤7, ≤30).
    event_type: 1=CON VIDA, 2=SIN VIDA, 3=DESCONOCIDA, 0=censurado/abierto.

    Valores esperados calculados a mano con la fórmula de Kalbfleisch &
    Prentice (ver docstring de _competing_risk_cif):
      día 1: n=10 en riesgo, 2 CON VIDA + 1 SIN VIDA -> CIF_1=0.2, CIF_2=0.1
      día 3: n=7  en riesgo, 1 CON VIDA + 1 SIN VIDA -> CIF_1=0.3, CIF_2=0.2
      día 7: n=5  en riesgo, 1 CON VIDA + 1 DESCONOCIDA -> CIF_1=0.4, CIF_3=0.1
      día 30: n=3 en riesgo, 1 SIN VIDA -> CIF_2=0.3
      quedan 2 censurados (S final = 0.2 = 2/10), consistente.
    """
    durations = [1, 1, 1, 3, 3, 7, 7, 30, 100, 100]
    events = [1, 1, 2, 1, 2, 1, 3, 2, 0, 0]
    return pd.Series(durations), pd.Series(events)


def test_cif_exact_ties_at_day_1_3_7_30_match_hand_calculation():
    durations, events = _synthetic_population()
    table = _competing_risk_cif(durations, events)
    expected = {
        1: {"cif_1": 0.2, "cif_2": 0.1, "cif_3": 0.0},
        3: {"cif_1": 0.3, "cif_2": 0.2, "cif_3": 0.0},
        7: {"cif_1": 0.4, "cif_2": 0.2, "cif_3": 0.1},
        30: {"cif_1": 0.4, "cif_2": 0.3, "cif_3": 0.1},
    }
    for day, exp in expected.items():
        row = table[table["days"] == day].iloc[0]
        for col, val in exp.items():
            assert row[col] == pytest.approx(val, abs=1e-9), f"day={day} {col}"


def test_cif_threshold_is_inclusive_of_the_exact_day():
    """Un evento EXACTAMENTE en el día 3 debe contar dentro de "≤3 días" --
    no debe requerirse < 3. Si el umbral fuera exclusivo, CIF_1 a ≤3 días
    sería 0.2 (solo el día 1) en vez de 0.3 (día 1 + día 3)."""
    durations, events = _synthetic_population()
    table = _competing_risk_cif(durations, events)
    sub = table[table["days"] <= 3]
    assert float(sub["cif_1"].iloc[-1]) == pytest.approx(0.3, abs=1e-9)


def test_cif_sum_of_all_event_types_equals_any_event_kaplan_meier():
    """Identidad matemática que debe cumplirse siempre (Kalbfleisch &
    Prentice): la suma de los CIF de todos los tipos de evento en un día
    dado debe igualar el Kaplan-Meier de "cualquier evento" (1 - S(t))
    sobre la misma población. Con el jitter de lifelines esta suma NO
    cerraba exactamente; con el cálculo exacto, sí."""
    from lifelines import KaplanMeierFitter

    durations, events = _synthetic_population()
    table = _competing_risk_cif(durations, events)
    kmf = KaplanMeierFitter()
    any_event = (events != 0).astype(int)
    kmf.fit(durations, any_event)
    for day in [1, 3, 7, 30]:
        row = table[table["days"] == day].iloc[0]
        cif_sum = row["cif_1"] + row["cif_2"] + row["cif_3"]
        any_event_pct = 1 - float(kmf.survival_function_at_times(day).iloc[0])
        assert cif_sum == pytest.approx(any_event_pct, abs=1e-9), f"day={day}"


def test_cif_handles_censoring_tied_with_an_event_on_the_same_day():
    """Regresión de un bug real encontrado durante la auditoría de la
    fecha de corte (ver CHANGELOG.md): la actualización de la
    supervivencia restaba la censura ADEMÁS de los eventos en el mismo
    paso, contando su efecto dos veces. Ese error era invisible mientras
    ningún caso censurado empataba con un evento real en el mismo día
    exacto -- exactamente lo que pasaba con el corte de censura
    incorrecto (`MAX(report_date, location_date)`), que alejaba
    artificialmente a los casos abiertos de los días tempranos. Al
    corregir el corte, empezaron a aparecer empates censura-evento y el
    bug se volvió visible. Este caso mínimo (4 personas, censura y
    evento empatados exactamente en el día 1) reproduce esa condición y
    debe coincidir exactamente con `lifelines.KaplanMeierFitter`,
    calculado de forma independiente."""
    from lifelines import KaplanMeierFitter

    durations = pd.Series([1, 1, 2, 3])
    events = pd.Series([1, 0, 1, 0])  # evento@1, censurado@1 (empate), evento@2, censurado@3

    table = _competing_risk_cif(durations, events)
    kmf = KaplanMeierFitter()
    kmf.fit(durations, (events != 0).astype(int))

    for day in [1, 2, 3]:
        row = table[table["days"] <= day].iloc[-1]
        cif_total = row["cif_1"]
        any_event_pct = 1 - float(kmf.survival_function_at_times(day).iloc[0])
        assert cif_total == pytest.approx(any_event_pct, abs=1e-9), f"day={day}"
    # Valor de referencia calculado a mano: a día 2, 1-S(2) = 0.625 (no
    # 0.5, que es lo que daba la fórmula con el bug).
    assert float(table[table["days"] <= 2].iloc[-1]["cif_1"]) == pytest.approx(0.625, abs=1e-9)


# ---------------------------------------------------------------------
# smoke tests del pipeline de desenlaces (requieren data/raw poblado;
# se saltan si no existe, igual que el smoke test general)
# ---------------------------------------------------------------------

def _build_fresh_db():
    from src.config import RAW_DIR, SUPPORTED_EXTENSIONS
    has_source = any(
        p.suffix.lower() in SUPPORTED_EXTENSIONS
        for p in RAW_DIR.iterdir() if p.is_file()
    ) if RAW_DIR.exists() else False
    if not has_source:
        pytest.skip("No hay archivo fuente en data/raw/; smoke test de desenlaces omitido.")

    from src.ingest import load_cases
    from src.quality import build_quality_flags
    from src.database import build_database

    cases, _ = load_cases()
    flags = build_quality_flags(cases, report_window_start=cases["report_date"].min())
    build_database(cases, flags)


def test_outcome_audit_reconciles_with_total_located():
    _build_fresh_db()
    from src.outcomes import export_outcome_audit
    audit = export_outcome_audit().set_index("chequeo")["valor"]
    total = audit["total_localizados"]
    con_vida = audit["con_vida"]
    sin_vida = audit["sin_vida"]
    desconocida = audit["condicion_desconocida"]
    # Invariante central del punto 1: la condición nunca se "pierde" --
    # todo localizado cae en exactamente una de las tres categorías.
    assert con_vida + sin_vida + desconocida == total


def test_outcome_intervals_denominator_matches_valid_duration_population():
    _build_fresh_db()
    from src.outcomes import export_outcome_intervals
    outputs = export_outcome_intervals()
    report_clock = outputs["report_clock"]
    # La suma de todas las celdas de la tabla de intervalos (reloj reporte)
    # debe igualar exactamente a los localizados con duración válida en
    # ese reloj -- ningún caso debe aparecer dos veces ni perderse.
    assert report_clock["total"].sum() == report_clock[["CON VIDA", "SIN VIDA", "DESCONOCIDA"]].to_numpy().sum()


def test_outcome_group_kpis_ci_bounds_are_valid():
    _build_fresh_db()
    from src.outcomes import export_outcome_group_kpis
    outputs = export_outcome_group_kpis()
    for name, df in outputs.items():
        valid = df[df["n_analitico"] > 0]
        assert (valid["ci95_low"] <= valid["pct_sin_vida"]).all(), name
        assert (valid["pct_sin_vida"] <= valid["ci95_high"]).all(), name
        assert (valid["ci95_low"] >= 0).all(), name
        assert (valid["ci95_high"] <= 100).all(), name


def test_competing_risk_naive_always_overestimates_correct_method():
    _build_fresh_db()
    from src.outcomes import export_outcome_competing_risk
    result = export_outcome_competing_risk()
    summary = result["summary"]
    # Este es el punto metodológico central del punto 4: el método ingenuo
    # (KM tratando el desenlace competidor como censura) SIEMPRE sobreestima
    # -- nunca subestima -- al estimador correcto (Aalen-Johansen). Si esta
    # prueba fallara, sería señal de un error de implementación, no un
    # hallazgo real.
    #
    # Se filtra a CON VIDA / SIN VIDA: DESCONOCIDA se exporta también en
    # este resumen (para que CON VIDA + SIN VIDA + DESCONOCIDA + S(t) sea
    # verificable), pero no tiene un "método ingenuo" comparable -- no es
    # un hallazgo del proyecto, solo existe para que la identidad de suma
    # cierre -- así que su columna ingenua queda NaN por diseño.
    comparable = summary[summary["desenlace"].isin(["CON VIDA", "SIN VIDA"])]
    assert (comparable["pct_ingenuo_km_mal_usado"] >= comparable["cif_pct_correcto_aalen_johansen"]).all()


def test_competing_risk_is_reproducible():
    _build_fresh_db()
    from src.outcomes import export_outcome_competing_risk
    r1 = export_outcome_competing_risk()["summary"]
    r2 = export_outcome_competing_risk()["summary"]
    # _competing_risk_cif es determinista (no usa ningún generador
    # aleatorio) -- correr el cálculo dos veces debe dar EXACTAMENTE el
    # mismo resultado, sin necesidad de fijar ninguna semilla. Esto ya no
    # depende de _AJ_SEED, que quedó sin uso tras retirar
    # lifelines.AalenJohansenFitter de este cálculo.
    assert r1["cif_pct_correcto_aalen_johansen"].tolist() == r2["cif_pct_correcto_aalen_johansen"].tolist()


def test_competing_risk_cif_sum_matches_any_event_km_on_real_data():
    """Misma identidad que test_cif_sum_of_all_event_types_equals_any_event_kaplan_meier
    pero sobre los datos reales del proyecto -- es la prueba de
    regresión que habría detectado el bug del jitter si hubiera existido
    desde el principio."""
    _build_fresh_db()
    from lifelines import KaplanMeierFitter
    from src.outcomes import export_outcome_competing_risk, _query
    from src.config import EXTRACT_CUTOFF_DATE

    result = export_outcome_competing_risk()
    cif_table = result["cif_table"]

    pop = _query("SELECT * FROM vw_outcome_competing_risk_input")
    import pandas as pd
    # Misma fecha de corte documentada que usa el código de producción
    # (src/outcomes.py) -- ya NO se re-infiere con MAX(report_date,
    # location_date) aquí tampoco, para no reintroducir por la puerta
    # trasera el mismo problema que se corrigió (ver CHANGELOG.md).
    cutoff = pd.to_datetime(EXTRACT_CUTOFF_DATE)
    # Misma re-censura por consistencia de corte que aplica la producción
    # (ver src/outcomes.py): un location_date posterior al corte no puede
    # ser un evento observado. Si esta prueba no replicara esa regla,
    # compararía el CIF ya corregido contra un KM de referencia que no lo
    # está -- una falsa alarma, no una verificación real.
    location_date = pd.to_datetime(pop["location_date"])
    observed_after_cutoff = (pop["event_type"] != 0) & (location_date > cutoff)
    pop.loc[observed_after_cutoff, "event_type"] = 0
    pop["duration"] = pop["report_to_location_days"].where(
        pop["event_type"] != 0,
        (cutoff - pd.to_datetime(pop["report_date"])).dt.days,
    )
    kmf = KaplanMeierFitter()
    any_event = (pop["event_type"] != 0).astype(int)
    kmf.fit(pop["duration"], any_event)

    for day in [1, 3, 7, 30]:
        row = cif_table[cif_table["days"] <= day].iloc[-1]
        cif_sum = row["cif_1"] + row["cif_2"] + row["cif_3"]
        any_event_pct = 1 - float(kmf.survival_function_at_times(day).iloc[0])
        assert cif_sum == pytest.approx(any_event_pct, abs=1e-6), f"day={day}"
