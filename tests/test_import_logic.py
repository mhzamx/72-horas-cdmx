"""Pruebas del pipeline 72 HORAS.

Se ejecutan con: pytest -q
No dependen de datos reales de personas: usan DataFrames sintéticos
pequeños para probar la LÓGICA (normalización, flags de calidad, KPIs),
nunca para simular el registro real.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.ingest import normalize_label, map_columns, prepare_cases, _normalize_placeholder_series
from src.quality import build_quality_flags, quality_summary


# ---------------------------------------------------------------------
# normalize_label / mapeo de columnas
# ---------------------------------------------------------------------

def test_normalize_label():
    assert normalize_label("Fecha de Localización") == "fecha_de_localizacion"
    assert normalize_label("Alcaldía de desaparición") == "alcaldia_de_desaparicion"


def test_map_columns_detects_real_source_headers():
    df = pd.DataFrame({
        "ID": [1],
        "Fecha.de.reporte.en.la.CBPCDMX": ["01/01/2020"],
        "Fecha.de.desaparicion": ["01/01/2020"],
        "Estatus.DESAPARECIDO": ["LOCALIZADO"],
    })
    mapped, info = map_columns(df)
    assert "report_date" in mapped.columns
    assert "missing_date" in mapped.columns
    assert "status" in mapped.columns
    assert info["missing_recommended"]  # location_date/sex/borough no están


def test_map_columns_raises_when_required_missing():
    df = pd.DataFrame({"Sexo": ["HOMBRE"]})
    with pytest.raises(ValueError):
        map_columns(df)


# ---------------------------------------------------------------------
# placeholders y age_group
# ---------------------------------------------------------------------

def test_placeholder_normalization_to_na():
    s = pd.Series(["IZTAPALAPA", "S/D", "S/D/", "SE DESCONOCE", None])
    out = _normalize_placeholder_series(s)
    assert out.iloc[0] == "IZTAPALAPA"
    assert pd.isna(out.iloc[1])
    assert pd.isna(out.iloc[2])
    assert pd.isna(out.iloc[3])
    assert pd.isna(out.iloc[4])


def test_prepare_cases_creates_age_group_and_case_key():
    df = pd.DataFrame({
        "report_date": ["01/01/2020", "02/01/2020"],
        "missing_date": ["01/01/2020", "01/01/2020"],
        "status": ["LOCALIZADO", "DESAPARECIDO"],
        "age": [8, 35],
    })
    out = prepare_cases(df)
    assert list(out["case_key"]) == [1, 2]
    assert out.loc[0, "age_group"] == "0-11"
    assert out.loc[1, "age_group"] == "30-44"


# ---------------------------------------------------------------------
# reglas de calidad: casos sintéticos que cubren cada categoría
# ---------------------------------------------------------------------

def _sample_cases() -> pd.DataFrame:
    return pd.DataFrame({
        "case_key": [1, 2, 3, 4, 5],
        "report_date": pd.to_datetime([
            "2020-01-10", "2020-01-10", "2020-01-10", "2020-01-10", None
        ]),
        "missing_date": pd.to_datetime([
            "2020-01-01", "2020-01-01", "2020-01-05", "2020-01-01", "2020-01-01"
        ]),
        "location_date": pd.to_datetime([
            "2020-01-12",  # caso 1: normal, localizado después del reporte
            "2020-01-05",  # caso 2: localizado ANTES del reporte pero después de desaparecer (ambiguo, no error)
            "2019-12-01",  # caso 3: localizado ANTES de desaparecer (imposible)
            None,          # caso 4: sin fecha de localización
            None,
        ]),
        "status": ["LOCALIZADO", "LOCALIZADO", "LOCALIZADO", "LOCALIZADO", "DESAPARECIDO"],
        "borough_missing": ["IZTAPALAPA", "IZTAPALAPA", "IZTAPALAPA", None, "COYOACAN"],
    })


def test_location_before_report_is_not_treated_as_impossible():
    cases = _sample_cases()
    flags = build_quality_flags(cases, report_window_start=pd.Timestamp("2020-01-01"))
    row2 = flags.loc[flags["case_key"] == 2].iloc[0]
    assert row2["location_before_report"] == True  # noqa: E712
    assert row2["location_before_event"] == False  # noqa: E712


def test_location_before_event_is_impossible():
    cases = _sample_cases()
    flags = build_quality_flags(cases, report_window_start=pd.Timestamp("2020-01-01"))
    row3 = flags.loc[flags["case_key"] == 3].iloc[0]
    assert row3["location_before_event"] == True  # noqa: E712


def test_status_located_without_location_date_flag():
    cases = _sample_cases()
    flags = build_quality_flags(cases, report_window_start=pd.Timestamp("2020-01-01"))
    row4 = flags.loc[flags["case_key"] == 4].iloc[0]
    assert row4["status_located_without_location_date"] == True  # noqa: E712


def test_missing_borough_flag():
    cases = _sample_cases()
    flags = build_quality_flags(cases, report_window_start=pd.Timestamp("2020-01-01"))
    row4 = flags.loc[flags["case_key"] == 4].iloc[0]
    assert row4["missing_borough"] == True  # noqa: E712


def test_quality_summary_categories_present():
    cases = _sample_cases()
    flags = build_quality_flags(cases, report_window_start=pd.Timestamp("2020-01-01"))
    summary = quality_summary(flags)
    assert set(summary["category"]) >= {"MISSING", "AMBIGUOUS", "IMPOSSIBLE", "MISMATCH"}
    # location_before_report cuenta TODO caso con loc<report, incluyendo los
    # que además son imposibles (loc<missing). Caso 2 (ambiguo puro) y caso 3
    # (imposible, que también queda antes del reporte) -> 2 en este fixture.
    # El número "legítimamente ambiguo" para reportar es
    # location_before_report - location_before_event (ver docs/METHODOLOGY.md).
    assert summary.loc[summary["check"] == "location_before_report", "affected_rows"].iloc[0] == 2
    assert summary.loc[summary["check"] == "location_before_event", "affected_rows"].iloc[0] == 1


# ---------------------------------------------------------------------
# smoke test del pipeline completo (requiere data/raw poblado; se salta
# si no existe, para que el repo clonado sin el archivo real no rompa CI)
# ---------------------------------------------------------------------

def test_pipeline_end_to_end_smoke():
    from src.config import RAW_DIR, SUPPORTED_EXTENSIONS
    has_source = any(
        p.suffix.lower() in SUPPORTED_EXTENSIONS
        for p in RAW_DIR.iterdir() if p.is_file()
    ) if RAW_DIR.exists() else False
    if not has_source:
        pytest.skip("No hay archivo fuente en data/raw/; smoke test omitido.")

    from src.ingest import load_cases
    cases, meta = load_cases()
    assert meta["rows"] == len(cases)
    assert "report_date" in cases.columns
    assert "missing_date" in cases.columns
    assert cases["case_key"].is_unique
