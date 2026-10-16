# Guía de Power BI — 72 HORAS

Esta es la guía completa para construir el dashboard. `POWER_BI_MODEL.md`
y `DAX_MEASURES.md` quedan como referencia rápida alineada con esta guía.

## 1. Archivos a importar

Desde `dashboard/data/` (esquema en estrella, regenerado por
`python -m src.run_all`):

| Archivo | Tipo | Grano |
|---|---|---|
| `fact_cases.csv` | Tabla de hechos | Un renglón por caso (`case_key`) |
| `dim_date.csv` | Dimensión | Un renglón por día del calendario cubierto |
| `dim_borough.csv` | Dimensión | Un renglón por alcaldía |

Desde `outputs/tables/` (agregados ya calculados en Python/SQL — se
importan **tal cual**, sin recalcular, para que los KPI del dashboard
coincidan exactamente con los del repositorio y con
`outputs/FINAL_FINDINGS.md`):

| Archivo | Para qué |
|---|---|
| `kpi_overview.csv` | Tarjetas KPI de la página 1. |
| `borough_kpis.csv`, `sex_kpis.csv`, `age_group_kpis.csv`, `year_kpis.csv` | Comparaciones por grupo (ya traen `sample_size` y `below_min_sample_size`). |
| `survival_curve.csv`, `survival_by_sex.csv`, `survival_by_borough_missing.csv`, `survival_by_age_group.csv` | Curvas de Kaplan-Meier (pregunta B). No se recalculan en DAX: la lógica de censura es más clara y auditable en Python (`src/analysis.py`). |
| `monthly_flow.csv`, `cohort_resolution.csv`, `pressure_signals.csv` | Página de tiempo/cohortes. |
| `data_quality_summary.csv` | Página de calidad. |

**No se importa** `data/raw/*.xlsx` directamente a Power BI: el
registro a nivel persona no debe circular fuera del pipeline controlado
(ver `docs/ETHICS.md`).

## 2. Relaciones

```
dim_date[date_key]  1 ── * fact_cases[report_date_key]     (activa)
dim_date[date_key]  1 ··· * fact_cases[missing_date_key]   (inactiva)
dim_date[date_key]  1 ··· * fact_cases[location_date_key]  (inactiva)
dim_borough[borough_missing] 1 ── * fact_cases[borough_missing]
```

Solo la relación con `report_date_key` se deja activa por defecto (es
el reloj central del proyecto). Las otras dos se activan puntualmente
con `USERELATIONSHIP()` dentro de una medida cuando se necesite analizar
por fecha de desaparición o de localización.

Las demás tablas (`kpi_overview`, `borough_kpis`, `survival_*`,
`monthly_flow`, `cohort_resolution`, `pressure_signals`,
`data_quality_summary`) se importan **sin relación** con `fact_cases`:
son resúmenes ya cerrados, no se cruzan a nivel de caso.

## 3. Medidas DAX (ver también `DAX_MEASURES.md`)

```DAX
Total Reportes = COUNTROWS(fact_cases)

Total Localizados = CALCULATE(COUNTROWS(fact_cases), fact_cases[is_located] = 1)

Casos Abiertos = [Total Reportes] - [Total Localizados]

% Abiertos = DIVIDE([Casos Abiertos], [Total Reportes])

-- Importante: esta medida responde la pregunta (A), "entre localizados".
-- Para la pregunta (B) usar la tabla survival_kpis importada, no DAX.
Localizados con duración válida =
CALCULATE(COUNTROWS(fact_cases), fact_cases[valid_for_report_timeline] = 1, fact_cases[is_located] = 1)

% Localizado ≤3d (entre localizados) =
VAR Numerador =
    CALCULATE(
        COUNTROWS(fact_cases),
        fact_cases[report_to_location_days] >= 0,
        fact_cases[report_to_location_days] <= 3
    )
RETURN DIVIDE(Numerador, [Localizados con duración válida])
```

> Regla del proyecto, también válida en Power BI: **nunca** mostrar
> `% Localizado ≤3d (entre localizados)` junto a un número que diga
> "% del total" sin la etiqueta que aclare cuál es cuál. Son las
> preguntas (A) y (B) de `docs/METHODOLOGY.md`.

## 4. Páginas sugeridas

### Página 1 — Resumen ejecutivo / 72 horas
- Tarjetas KPI (de `kpi_overview.csv`): total de reportes, localizados,
  abiertos, % ≤1/≤3/≤7/≤30 días entre localizados.
- Una segunda fila de tarjetas con los mismos umbrales pero desde
  `survival_kpis.csv` (pregunta B), etiquetada explícitamente distinta.
- Línea: curva de Kaplan-Meier (`survival_curve.csv`).
- Filtro de página: año de reporte.

### Página 2 — Geografía / alcaldías
- Mapa o barras horizontales: `borough_kpis.csv`, solo alcaldías con
  `below_min_sample_size = 0`.
- Tabla con `sample_size`, `located_records`, `open_records`,
  `pct_located_le_3d_among_located`, `avg_report_to_location_days`.
- Slicer: alcaldía (`dim_borough`).

### Página 3 — Tiempo y cohortes
- Línea: `monthly_flow.csv` (reportes vs. localizaciones).
- Línea: `cohort_resolution.csv`, `pct_matured_reports_located_le_3d`
  filtrando `matured_3d_denominator >= 30`.
- Tabla/resaltado: meses de `pressure_signals.csv` con
  `pressure_signal = 1`.
- Slicer: rango de fechas (`dim_date`, relación activa con
  `report_date_key`).

### Página 4 — Calidad y metodología
- Barras: `data_quality_summary.csv` (`affected_rows` o `pct_rows` por
  `check`, coloreado por `category`).
- Texto/tarjeta explicando la distinción AMBIGUOUS vs. IMPOSSIBLE
  (tomado de `docs/METHODOLOGY.md`, sección 4).
- Enlace o texto con las advertencias de `outputs/FINAL_FINDINGS.md`
  sección 9 ("Qué NO dice este análisis").

## 5. Filtros y KPI cards recomendados

- Slicers globales (todas las páginas): año de reporte, sexo, grupo de
  edad, alcaldía.
- KPI card siempre visible: `Total Reportes`, `% Abiertos` — para que
  nunca se pierda de vista cuánta población está censurada.
- Evitar gráficos de pastel para comparar alcaldías (demasiadas
  categorías); usar barras horizontales ordenadas.

## 6. Por qué no hay `dim_sex` / `dim_age_group`

Sexo (2 valores) y grupo de edad (6 valores) se dejan como columnas
planas en `fact_cases`. Crear dimensiones separadas para catálogos tan
pequeños añade joins innecesarios sin beneficio de rendimiento ni
claridad — es sobre-ingeniería para este volumen de datos (2,958 filas).
