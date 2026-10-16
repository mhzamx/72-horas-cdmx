from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_TABLES = ROOT / "outputs" / "tables"
OUTPUT_CHARTS = ROOT / "outputs" / "charts"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DB_PATH = PROCESSED_DIR / "72_horas.db"

for path in [RAW_DIR, PROCESSED_DIR, OUTPUT_TABLES, OUTPUT_CHARTS, DASHBOARD_DATA]:
    path.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# ---------------------------------------------------------------------
# Fecha de corte administrativo del extracto (para censura por la
# derecha en supervivencia/riesgos competitivos: la fecha "hasta la
# cual" se considera observado un caso que sigue abierto).
#
# CORREGIDO (ver CHANGELOG.md): antes se inferÍa automáticamente como
# MAX(report_date, location_date) sobre todos los casos. Eso rompió con
# el caso ID 1138 (LOCALIZADO, reportado 2021-09-07, con
# `location_date` = 2022-12-15): esa única fecha, más de 15 meses
# después de su reporte y muy fuera de línea respecto a los casos
# vecinos por ID (todos localizados en días o semanas desde su
# reporte), desplazó el corte global de todo el proyecto un mes
# completo -- de 2022-11-15 a 2022-12-15 -- sin ninguna revisión. No
# hay evidencia documental que confirme si esa fecha es un desenlace
# real muy tardío o un error de captura (posible: año mal tecleado); no
# se declara ninguna de las dos cosas como cierta. Lo que sí es un
# error metodológico, independientemente de esa duda, es usar el
# máximo de una columna de eventos como sustituto automático de "la
# fecha en que se congeló el extracto": un solo registro atípico no
# debería poder mover un parámetro que afecta a los 1,181 casos
# abiertos del proyecto.
#
# Valor elegido: 2022-11-15. Evidencia disponible (ver
# docs/SOURCE_ACCESS.md): (a) el nombre del archivo,
# `registro-interno-cbp-15-noviembre.xlsx`, nombra explícitamente esa
# fecha; (b) el último reporte real en los datos es 2022-11-14 -- un
# día antes, consistente con un extracto que captura reportes completos
# hasta esa fecha y se etiqueta "al 15 de noviembre". Esto es evidencia
# interna consistente, NO una confirmación externa/oficial de que el
# extracto se generó exactamente ese día -- se documenta como la mejor
# suposición disponible, no como un hecho confirmado.
#
# Por esa incertidumbre residual, se corrió un análisis de sensibilidad
# comparando este valor contra el corte anterior (2022-12-15, derivado
# del outlier) -- ver CHANGELOG.md para las cifras exactas que cambian
# y cuáles no.
#
# Usado en: sql/02_views.sql (`vw_report_cohorts`, `vw_survival_input`
# -- como literal, porque esas vistas son SQL estático sin templating;
# si este valor cambia, debe actualizarse también ahí) y
# src/outcomes.py (`export_outcome_competing_risk`, como constante
# Python).
EXTRACT_CUTOFF_DATE = "2022-11-15"

# v0.2 (doc 03): alias usado por src/estimands.py; mismo valor que EXTRACT_CUTOFF_DATE.
CUTOFF_DATE = EXTRACT_CUTOFF_DATE
DASHBOARD_DATA_V02 = ROOT / "dashboard" / "data_v02"
DASHBOARD_DATA_V02.mkdir(parents=True, exist_ok=True)
