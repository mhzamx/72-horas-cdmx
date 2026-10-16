"""Pruebas v0.2 (doc 03 §6-C5). Archivo nuevo: no modifica las 20 pruebas previas."""
from __future__ import annotations

import hashlib
import numpy as np
import pytest

RAW_SHA256 = "acace3f70109a79181389f3af4c41f44a73e6b33661b7fc423a6b170aa3d9619"


@pytest.fixture(scope="module")
def v():
    from src.config import RAW_DIR, SUPPORTED_EXTENSIONS
    if not (RAW_DIR.exists() and any(p.suffix.lower() in SUPPORTED_EXTENSIONS for p in RAW_DIR.iterdir())):
        pytest.skip("No hay archivo fuente en data/raw/; pruebas v0.2 omitidas.")
    from src.ingest import load_cases
    from src.quality import build_quality_flags
    from src.database import build_database
    from src.estimands import load_classified
    cases, _ = load_cases()
    build_database(cases, build_quality_flags(cases, report_window_start=cases["report_date"].min()))
    return load_classified()


def test_population_classes_sum_and_counts(v):
    counts = v["population_class"].value_counts().to_dict()
    assert len(v) == 2958
    assert counts == {"VALIDO": 1211, "ABIERTO": 1181, "AMBIGUO": 318, "SIN_FECHA": 227, "IMPOSIBLE": 21}


def test_scenario_ordering(v):
    from src.estimands import scenario_arrays, km_pct, e3_estimate
    pct = {sc: km_pct(*scenario_arrays(v, sc)[1:3]) for sc in ("E0", "E2-baja", "E2-alta")}
    e3 = e3_estimate(v, M=50)["km"]
    assert np.all(pct["E0"] <= pct["E2-baja"] + 1e-9)
    assert np.all(pct["E2-baja"] <= e3 + 1e-9)
    assert np.all(e3 <= pct["E2-alta"] + 1e-9)


def test_aj_exact_sums_to_km(v):
    from src.estimands import scenario_arrays, aj_exact, km_curve
    for sc in ("E0", "E1", "E2-alta"):
        _, dur, ev, st = scenario_arrays(v, sc)
        t, cif, S_aj = aj_exact(dur, st)
        tk, S_km = km_curve(dur, ev)
        assert np.allclose(cif.sum(axis=0), 1 - S_km, atol=1e-9)
        assert np.allclose(S_aj, S_km, atol=1e-12)


def test_e3_reproducible(v):
    from src.estimands import e3_estimate
    a, b = e3_estimate(v, M=30), e3_estimate(v, M=30)
    assert np.array_equal(a["km"], b["km"]) and np.array_equal(a["aj"], b["aj"])


def test_no_event_after_cutoff(v):
    import pandas as pd
    from src.config import CUTOFF_DATE
    from src.estimands import scenario_arrays
    cut = pd.Timestamp(CUTOFF_DATE)
    max_fu = (cut - v["rd"]).dt.days.max()
    for sc in ("E0", "E1", "E2-baja", "E2-alta"):
        m, dur, ev, _ = scenario_arrays(v, sc)
        fu = v.loc[m, "follow_up_days"].to_numpy()
        assert np.all(dur[ev == 1] <= fu[ev == 1])
        assert dur[ev == 0][dur[ev == 0] < 1e8].max() <= max_fu


def test_outcome_intervals_v02_only_valid(v):
    """La tabla de intervalos del tablero usa solo la clase VALIDO (sin orden imposible)."""
    from src.estimands import export_outcome_intervals_v02
    t = export_outcome_intervals_v02(v)
    assert int(t["total"].sum()) == int((v["population_class"] == "VALIDO").sum())
    assert (t[["CON VIDA", "SIN VIDA", "DESCONOCIDA"]].sum(axis=1) == t["total"]).all()


def test_raw_source_untouched():
    from src.config import RAW_DIR
    f = RAW_DIR / "registro-interno-cbp-15-noviembre.xlsx"
    if not f.exists():
        pytest.skip("Sin archivo fuente.")
    assert hashlib.sha256(f.read_bytes()).hexdigest() == RAW_SHA256
