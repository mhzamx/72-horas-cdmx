from __future__ import annotations

import re
import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

from .config import RAW_DIR, SUPPORTED_EXTENSIONS

# ---------------------------------------------------------------------------
# Columnas canónicas del proyecto.
#
# Incluye variantes genéricas y los nombres EXACTOS observados en
# registro-interno-cbp-15-noviembre.xlsx (fuente: CBPCDMX, Versión Pública
# del Registro Interno de Personas Desaparecidas). Ver docs/data_dictionary.md
# para el significado de cada variable y sus advertencias de calidad.
# ---------------------------------------------------------------------------
ALIASES = {
    "source_id": ["ID", "id", "folio", "identificador"],
    "report_date": [
        "Fecha.de.reporte.en.la.CBPCDMX",
        "fecha_reporte", "fecha_de_reporte", "fecha_registro",
        "report_date", "fecha_en_que_se_recibio_el_reporte",
    ],
    "missing_date": [
        "Fecha.de.desaparicion",
        "fecha_hechos", "fecha_de_los_hechos", "fecha_desaparicion",
        "fecha_de_desaparicion", "missing_date", "event_date",
    ],
    "location_date": [
        "Fecha.de.localizacion",
        "fecha_localizacion", "fecha_de_localizacion", "location_date",
    ],
    "status": [
        "Estatus.DESAPARECIDO",
        "estatus", "estatus_registro", "estatus_de_la_persona", "status",
    ],
    "sex": ["Sexo", "sexo", "sex"],
    "age": ["Edad", "edad", "age"],
    "nationality": ["Nacionalidad", "nacionalidad", "nationality"],
    "birthplace": ["Lugar.de.nacimiento", "lugar_de_nacimiento"],
    "education": ["Escolaridad", "escolaridad"],
    "marital_status": ["Estado.civil", "estado_civil"],
    "state_missing": ["Entidad.de.desaparicion", "entidad_de_desaparicion"],
    "borough_missing": [
        "Municipio.Alcadia.de.la.desaparicion",
        "municipio_alcadia_de_la_desaparicion",
        "alcaldia", "alcaldia_desaparicion", "alcaldia_de_desaparicion",
        "municipio_desaparicion", "municipality_of_disappearance",
        "municipio_alcaldia_hechos",
    ],
    "colonia_missing": ["Colonia.de.la.desaparicion", "colonia_de_la_desaparicion"],
    "disappearance_circumstances": [
        "Circunstancias.de.la.desaparicion", "circunstancias_de_la_desaparicion"
    ],
    "borough_location": [
        "Municipio.Alcaldia.de.la.localizacion",
        "municipio_alcaldia_de_la_localizacion",
        "alcaldia_localizacion", "alcaldia_de_localizacion",
    ],
    "report_source": [
        "Fuente.de.reporte", "fuente_de_reporte", "fuente_reporte"
    ],
    "location_condition": [
        "Condicion.localizacion", "condicion_localizacion"
    ],
    "health_status": [
        "Estado.de.Salud", "estado_de_salud"
    ],
    "location_place_type": [
        "Tipo.de.lugar.de.la.localizacion", "tipo_de_lugar_de_la_localizacion"
    ],
    "disappearance_reason": [
        "Motivo.referido.de.desaparicion", "motivo_referido_de_desaparicion"
    ],
    "state_location": [
        "Entidad.de.localizacion", "entidad_localizacion", "entidad_de_localizacion",
        "estado_localizacion", "geographic_state_of_location",
    ],
}

REQUIRED_CORE = ["report_date", "missing_date", "status"]
RECOMMENDED = ["location_date", "sex", "borough_missing"]

# Tokens que en este registro significan "sin dato", no una categoría real.
# Se ven en varias columnas de texto libre/catálogo (alcaldía, nacionalidad).
PLACEHOLDER_TOKENS = {"S/D", "S/D/", "SE DESCONOCE", "N/D", "NO DISPONIBLE", ""}

# Columnas de texto/categoría donde vale la pena normalizar placeholders.
CATEGORICAL_COLUMNS = [
    "status", "sex", "nationality", "birthplace", "education", "marital_status",
    "state_missing", "borough_missing", "colonia_missing",
    "disappearance_circumstances", "borough_location", "report_source",
    "location_condition", "health_status", "location_place_type",
    "disappearance_reason", "state_location",
]

# Cortes de grupo de edad. Son una elección analítica nuestra (no vienen así
# en el archivo fuente, que trae edad en años); documentado en
# docs/data_dictionary.md. Los cortes separan niñez/adolescencia porque son
# categorías con dinámicas de búsqueda distintas y suelen priorizarse.
AGE_BINS = [-0.01, 11, 17, 29, 44, 59, 200]
AGE_LABELS = ["0-11", "12-17", "18-29", "30-44", "45-59", "60+"]


def normalize_label(value: str) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def discover_source() -> Path:
    candidates = [
        p for p in RAW_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not candidates:
        raise FileNotFoundError(
            "No encontré un CSV/XLS/XLSX en data/raw/. "
            "Coloca ahí la copia oficial del registro."
        )
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise RuntimeError(
            f"Hay más de un archivo fuente en data/raw/: {names}. "
            "Deja solo la versión que deseas analizar."
        )
    return candidates[0]


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        attempts = [
            dict(encoding="utf-8-sig", sep=None, engine="python"),
            dict(encoding="utf-8", sep=None, engine="python"),
            dict(encoding="latin-1", sep=None, engine="python"),
        ]
        last = None
        for kwargs in attempts:
            try:
                return pd.read_csv(path, **kwargs)
            except Exception as exc:
                last = exc
        raise last
    return pd.read_excel(path)


def map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    original = list(df.columns)
    normalized = {col: normalize_label(col) for col in original}
    reverse = {}
    for col, norm in normalized.items():
        reverse.setdefault(norm, col)

    rename = {}
    matched = {}

    for canonical, aliases in ALIASES.items():
        for alias in [canonical] + aliases:
            key = normalize_label(alias)
            if key in reverse:
                source_col = reverse[key]
                rename[source_col] = canonical
                matched[canonical] = source_col
                break

    out = df.rename(columns=rename).copy()

    missing_core = [c for c in REQUIRED_CORE if c not in out.columns]
    if missing_core:
        raise ValueError(
            "Faltan columnas esenciales después de mapear el archivo: "
            + ", ".join(missing_core)
            + "\nColumnas recibidas: "
            + ", ".join(map(str, original))
        )

    return out, {
        "original_columns": [str(x) for x in original],
        "matched_columns": matched,
        "missing_recommended": [c for c in RECOMMENDED if c not in out.columns],
    }


def _normalize_placeholder_series(series: pd.Series) -> pd.Series:
    """Convierte tokens tipo 'S/D', 'S/D/', 'SE DESCONOCE' en NA real.

    Estos tokens existen en el archivo original como forma de capturar
    "sin dato". Si no se normalizan, contaminan los agrupamientos (por
    ejemplo, aparecerían como si fueran una alcaldía real). No se borra
    ninguna fila: solo se convierte el valor de la celda a NA para que
    las reglas de calidad (missing_alcaldia, etc.) los cuenten correctamente.
    """
    cleaned = series.astype("string").str.strip()
    cleaned = cleaned.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    upper = cleaned.str.upper()
    is_placeholder = upper.isin(PLACEHOLDER_TOKENS)
    return cleaned.mask(is_placeholder.fillna(False), pd.NA)


def prepare_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el DataFrame ya mapeado (nombres canónicos) en la capa
    "cleaned": tipos correctos, placeholders normalizados a NA, y columnas
    derivadas (age_group). NO elimina filas ni corrige fechas "raras":
    eso es responsabilidad de src/quality.py, que las deja documentadas
    como flags en vez de borrarlas en silencio.
    """
    out = df.copy()

    for col in ["report_date", "missing_date", "location_date"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce", dayfirst=True)

    for col in CATEGORICAL_COLUMNS:
        if col in out.columns:
            out[col] = _normalize_placeholder_series(out[col])

    if "age" in out.columns:
        out["age"] = pd.to_numeric(out["age"], errors="coerce")
        out["age_group"] = pd.cut(
            out["age"], bins=AGE_BINS, labels=AGE_LABELS
        ).astype("string")

    if "source_id" in out.columns:
        out["source_id"] = pd.to_numeric(out["source_id"], errors="coerce").astype("Int64")

    out.insert(0, "case_key", range(1, len(out) + 1))
    return out


def load_cases() -> tuple[pd.DataFrame, dict]:
    source = discover_source()
    raw = read_source(source)
    mapped, mapping = map_columns(raw)
    cases = prepare_cases(mapped)

    meta = {
        "source_file": source.name,
        "rows": int(len(cases)),
        "columns": int(len(cases.columns)),
        **mapping,
    }
    return cases, meta
