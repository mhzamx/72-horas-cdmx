# 72 HORAS
## Auditoría de la velocidad de localización de personas desaparecidas — Ciudad de México

**Proyecto de portafolio de Data Analyst.**

### Resultado principal (v0.2 final)

Con los mismos 2,958 registros, el porcentaje de casos con localización documentada en
≤3 días va de **34.0% a 46.2%** según cómo se traten los datos incompletos.

| Indicador (población E3, 2,937 casos) | Valor |
|---|---|
| Localización documentada ≤3 días (estimación principal) | **44.2%** (IC 95% 42.3–46.2%) |
| Rango de sensibilidad (227 localizados sin fecha) | 38.5–46.2% |
| Versión anterior del análisis (E0) | 34.0% |
| Localización documentada a 30 días | 56.8% (51.8% con vida · 4.4% sin vida · 0.6% desconocido) |
| Casos abiertos al corte (15-nov-2022) | 1,181 |

- La estimación incluye 318 casos localizados antes de que se registrara el reporte,
  contados como día 0.
- La fuente no contiene horas: ≤3 días calendario es la aproximación operativa de las
  primeras 72 horas. 72 horas es un hito de medición, no un plazo de espera: la búsqueda
  debe iniciar de inmediato.
- La fecha de localización es la registrada; no es fecha de fallecimiento.
- Tablero: `powerbi/72HORAS_v02_final.pdf` (5 páginas) y `powerbi/72HORAS_v02_final.pbix`.

**Este repositorio no incluye datos a nivel de persona.** El archivo fuente es público
(ver `docs/SOURCE_ACCESS.md`); para reproducir el análisis, descárgalo y colócalo en
`data/raw/`.

### Pregunta central

> ¿Qué ocurre durante las primeras 72 horas posteriores al reporte de
> una desaparición, y qué factores están asociados con una localización
> más rápida o más lenta?

### Pregunta rectora v0.2 (aprobada por Miguel el 11-oct-2026)

> ¿Qué proporción de los casos recibidos por la CBPCDMX entre 2019 y 2022
> tiene localización documentada dentro de los 3 días posteriores al
> reporte, y qué características registradas se asocian con una
> localización más rápida o más lenta?

- **S1.** ¿Cuánto cambia esa proporción según cómo se traten los casos
  abiertos, los localizados antes del registro y las fechas faltantes?
- **S2.** ¿Qué parte de esas localizaciones es con vida y qué parte sin vida?
- **S3.** ¿Qué tan confiable es el estatus "abierto" del registro?

La pregunta de arriba es la formulación original (se conserva por
trazabilidad); la v0.2 la precisa sin cambiar su reloj (desde el reporte)
ni su intención (factores asociados).

El proyecto no predice qué persona desaparecerá ni atribuye causalidad
individual. Mide **tiempos, calidad del registro y patrones agregados**
usando el registro público oficial, y es explícito sobre los límites de
lo que esos datos permiten concluir.

## Datos

**Fuente:** Comisión de Búsqueda de Personas de la Ciudad de México
(CBPCDMX) — Versión Pública del Registro Interno de Personas
Desaparecidas. Archivo usado: `registro-interno-cbp-15-noviembre.xlsx`
(2,958 casos, reportes del 2019-06-25 al 2022-11-14). Ver
`docs/SOURCE_ACCESS.md` para la verificación de procedencia y
`docs/DATA_DICTIONARY.md` para cada columna.

`data/raw/` es una fuente congelada: el pipeline nunca la modifica ni la
sobrescribe.

> **v0.2 (2026-10-11):** la estimación de "% localizado a ≤3 días" se corrigió a
> **44.2%** (IC 95% 42.3–46.2; rango 38.5–46.2 según el tratamiento de 227
> localizados sin fecha). La cifra de 34.0% citada abajo excluía 564 casos
> localizados. Ver `outputs/FINAL_FINDINGS.md` §18 y `docs/METHODOLOGY.md` §13.

## Historia del análisis (v0.1 → v0.2)

En la v0.1, entre los casos **ya localizados**, el 67.1% se resolvió en ≤3 días desde el
reporte; al incorporar los casos abiertos con Kaplan-Meier (censura), la estimación bajaba a
34.0%. La v0.2 mostró que esa cifra dejaba fuera 564 localizados; 545 de ellos (318 antes
del registro y 227 sin fecha) entran en la población completa, y los 19 con orden de fechas
imposible siguen excluidos. Con la población completa e imputación múltiple, la estimación
principal es 44.2%. Detalle completo, con todos los denominadores explícitos, en
`outputs/FINAL_FINDINGS.md` (§18) y `docs/METHODOLOGY.md` (§13).

**Ampliación (§11-§17 de `outputs/FINAL_FINDINGS.md`):** de los
localizados, ¿el desenlace fue CON VIDA o SIN VIDA, y cómo se asocia
con el tiempo transcurrido? Se modela con riesgos competitivos
(Aalen-Johansen), no con Kaplan-Meier simple — ver por qué en
`docs/METHODOLOGY.md` §12. Incluye una advertencia explícita: la fecha
de localización no es la fecha de fallecimiento, y ningún número de
esa sección se usa para afirmar causalidad ni para declarar el
proyecto terminado.

## Qué demuestra técnicamente

- **Python / pandas:** ingesta tolerante a variantes de columnas,
  normalización de placeholders, validación de fechas, 25
  pruebas unitarias (`pytest`).
- **SQL / SQLite:** vistas encadenadas, CTEs, funciones de ventana
  (`RANK`, `ROW_NUMBER`, `LAG`, promedios móviles), `HAVING` para
  imponer tamaño mínimo de muestra (`sql/`).
- **Calidad de datos:** 9 reglas clasificadas en 6 categorías
  (faltante, imposible, ambiguo, inconsistente, duplicado, outlier),
  ninguna fila eliminada en silencio (`src/quality.py`,
  `docs/METHODOLOGY.md`).
- **Estadística:** distribución de tiempos (mediana/P75/P90/P95),
  cohortes maduras vs. inmaduras, Kaplan-Meier implementado desde cero
  y explicable paso a paso.
- **Visualización:** 9 gráficos, cada uno respondiendo una pregunta
  específica (`outputs/charts/`).
- **Riesgos competitivos:** desenlace CON VIDA/SIN VIDA modelado con
  Aalen-Johansen, con la comparación explícita contra el método ingenuo
  (KM simple mal usado) que documenta el sesgo de no usarlo
  (`src/outcomes.py`, `docs/METHODOLOGY.md` §12).
- **Power BI:** tablero de 5 páginas (`powerbi/`), modelo agregado generado como
  proyecto PBIP/TMDL desde Python (`powerbi/build_pbip_72h_r.py`), con segmentadores.
- **Comunicación:** resumen ejecutivo y hallazgos finales con denominadores
  explícitos (`docs/`, `outputs/`).

## Ejecución

```powershell
# Desde la raíz del proyecto
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.run_all
```

El pipeline (`src/run_all.py`):

1. detecta el CSV/XLS/XLSX en `data/raw/`;
2. normaliza nombres de columnas y valores placeholder;
3. valida fechas y calcula flags de calidad (sin borrar filas);
4. construye `data/processed/72_horas.db` (SQLite);
5. exporta KPI y tablas analíticas a `outputs/tables/`;
6. calcula distribución de tiempos y supervivencia (general y por
   grupo);
7. detecta señales de presión operativa;
8. genera 6 gráficos en `outputs/charts/`;
9. exporta el esquema en estrella para Power BI a `dashboard/data/`;
10. audita desenlaces CON VIDA/SIN VIDA, calcula riesgos competitivos
    (Aalen-Johansen) y genera 3 gráficos adicionales (`src/outcomes.py`).

Para reproducir desde cero: clonar el repositorio, colocar
**únicamente** la copia oficial del registro en `data/raw/` (el
`.gitignore` excluye ese archivo del repositorio por defecto — ver
`docs/ETHICS.md`) y correr el comando de arriba. `tests/` incluye un
smoke test que se omite automáticamente si no hay archivo fuente.

```bash
pytest -q
```

## Estructura

```text
72-horas/
├── data/
│   ├── raw/               # fuente original, nunca se modifica
│   ├── processed/         # SQLite y metadata generados
│   └── source_contract.json
├── sql/
│   ├── 01_schema.sql
│   ├── 02_views.sql       # capa "analytical": población de cada análisis
│   └── 03_analysis_queries.sql  # consultas de portafolio (CTE, window functions)
├── src/
│   ├── config.py
│   ├── ingest.py          # capa "cleaned"
│   ├── quality.py         # reglas de calidad clasificadas
│   ├── database.py
│   ├── analysis.py        # KPI, supervivencia, cohortes
│   ├── outcomes.py        # desenlaces CON VIDA/SIN VIDA, riesgos competitivos
│   ├── charts.py
│   ├── powerbi_export.py  # esquema en estrella
│   └── run_all.py
├── tests/
│   ├── test_import_logic.py
│   └── test_outcomes.py
├── outputs/
│   ├── tables/
│   ├── charts/
│   └── FINAL_FINDINGS.md
├── powerbi/                # tablero final (.pbix, .pdf), modelo agregado y generador
├── dashboard/
│   ├── data/               # dim_date, dim_borough (fact_cases no se publica)
│   ├── data_v02/           # tablas agregadas v0.2
│   ├── POWER_BI_GUIDE.md
│   ├── POWER_BI_MODEL.md
│   └── DAX_MEASURES.md
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── METHODOLOGY.md
│   ├── ETHICS.md
│   ├── SOURCE_ACCESS.md
│   ├── RESEARCH_LOG.md
│   └── executive_summary.md
├── CHANGELOG.md
└── requirements.txt
```

## Limitaciones (ver `docs/ETHICS.md` y `outputs/FINAL_FINDINGS.md` §9)

- Cubre solo 2019-06-25 a 2022-11-14: no incluye lo ocurrido después.
- No equivale a la totalidad de personas desaparecidas de Ciudad de
  México en el registro nacional (RNPDNO).
- Mide fechas registradas, no la calidad de las diligencias de
  búsqueda en sí.
- Ninguna comparación entre grupos implica causalidad.

## Próximos pasos

- Incorporar un extracto más reciente del registro cuando esté
  disponible y comparar cohortes entre vintages (el pipeline ya está
  preparado para aceptar cualquier archivo con las mismas columnas).
- Explorar, con datos internos (no públicos), la descomposición del
  tiempo total en etapas del proceso de búsqueda.
