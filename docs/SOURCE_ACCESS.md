# Acceso a la fuente — estado documentado

## Lo confirmado

La página oficial de la Comisión de Búsqueda de Personas de la Ciudad de México describe una versión pública del Registro Interno y especifica que contiene, entre otras variables:

- fecha en que se recibió el reporte;
- fecha de los hechos;
- alcaldía y colonia de los hechos;
- estatus desaparecida/localizada;
- para localizadas: fecha y entidad/municipio o alcaldía de localización.

URL oficial:
`https://comisiondebusqueda.cdmx.gob.mx/CBP/rpd/version-publica`

Una guía técnica de la Comisión de Derechos Humanos de la Ciudad de México publicada en 2024 documentó que la versión pública con datos hasta el **30 de junio de 2023** estaba disponible como una **tabla de Excel** y que el vínculo de descarga se encontraba al final de la página.

Un artículo de PLOS ONE publicado en 2025 (Aguilar-Velázquez et al.) documentó haber usado una copia con **3,450 registros** y nueve columnas analíticas, incluyendo `report date`, `missing date`, `status` y `location date`.

## Archivo obtenido y verificado

El proyecto ya cuenta con una copia oficial del registro:
`data/raw/registro-interno-cbp-15-noviembre.xlsx` — **2,958 filas × 21
columnas**. Verificación realizada antes de usarlo:

- Las 21 columnas originales corresponden, una a una, al catálogo de
  variables que describe la página oficial (fecha de reporte, fecha de
  hechos, alcaldía/colonia, estatus, fecha y condición de localización,
  entre otras). Detalle completo en `docs/DATA_DICTIONARY.md`.
- La ventana real observada de `report_date` es **2019-06-25 a
  2022-11-14**. Es un corte **anterior** al 30/06/2023 mencionado en la
  guía de 2024, y también distinto del extracto de 3,450 filas
  (2019–2023) que usó el estudio de PLOS ONE. El nombre del archivo
  ("15 noviembre") es consistente con esa fecha de corte real.
- Conclusión: es un extracto oficial **más antiguo** del mismo
  registro interno, no una fuente alternativa, no una muestra
  reconstruida y no un archivo de menor calidad. Se documenta la
  diferencia de cobertura en vez de ocultarla.

Esta discrepancia de vintage se refleja en todos los hallazgos
(`outputs/FINAL_FINDINGS.md`), que aplican estrictamente al periodo
2019-06-25 a 2022-11-14 observado en este archivo — no a la totalidad
del historial del registro ni al periodo del estudio académico.

## Fecha de corte administrativo del extracto (auditoría)

La sección anterior establece que el archivo cubre reportes hasta
2022-11-14 y que su nombre nombra explícitamente "15 noviembre". Ese
mismo dato se usa en el análisis de supervivencia como fecha de corte
para censurar los casos que siguen abiertos (`EXTRACT_CUTOFF_DATE` en
`src/config.py`), pero llegar a ese valor requirió una auditoría
específica porque el método original para inferirlo era frágil.

**El problema encontrado.** El corte se calculaba antes como
`MAX(report_date, location_date)` sobre todo el dataset — es decir, la
fecha de evento más tardía de cualquier columna, de cualquier caso. Un
solo registro, **ID 1138**, tiene `location_date = 2022-12-15`: más de
15 meses después de su propio reporte (2021-09-07) y posterior a
*cualquier otra* fecha de localización del archivo completo (la
siguiente más tardía es 2022-11-10, más de un mes antes). Ese único
valor bastaba para mover el corte de todo el proyecto de 2022-11-15 a
2022-12-15, afectando la censura de los 1,181 casos abiertos.

**El caso ID 1138 en sí — evidencia disponible, sin conclusión
forzada.** Reportado 2021-09-07, desaparición 2021-08-14, estatus
LOCALIZADO, condición CON VIDA, `location_date` 2022-12-15. Sus
vecinos inmediatos por ID (1133 a 1140, reportados en la misma semana
de septiembre de 2021) se localizaron todos en días o semanas desde su
reporte, no meses. Por otro lado, el ID y `report_date` tienen una
correlación de **-0.996** en todo el archivo (IDs bajos = reportes más
recientes, consistente con una secuencia asignada en orden
cronológico inverso al compilar el extracto) — si `location_date`
tuviera un error de captura en el año, no habría razón para que el
`ID` de ese mismo registro también encajara perfectamente en esa
secuencia, pero tampoco es evidencia de que la fecha sea correcta. No
hay en este archivo ningún campo de auditoría, log de cambios o fuente
secundaria que permita decidir entre "resolución real 15 meses
después" y "error de captura en `location_date`". Se documenta la
anomalía; no se declara el caso legítimo ni erróneo.

**Decisión y evidencia para 2022-11-15.** (a) el nombre del archivo,
`registro-interno-cbp-15-noviembre.xlsx`, nombra esa fecha
explícitamente; (b) el último reporte real en los datos es
2022-11-14, un día antes — consistente con un extracto que se
etiqueta "al 15 de noviembre" y captura reportes completos hasta el
día anterior. Esto es evidencia interna consistente, **no** una
confirmación oficial/externa de la fecha exacta de generación del
extracto. Se adoptó como constante explícita y documentada
(`src/config.py::EXTRACT_CUTOFF_DATE`) precisamente para que quede
señalada como una suposición razonada, no como un hecho verificado ni
como un nuevo cálculo automático que un futuro registro atípico pueda
volver a desplazar sin revisión.

**Análisis de sensibilidad (2022-11-15 vs. 2022-12-15).** La mayoría
de los resultados reportados cambia poco o nada: el Kaplan-Meier
general a ≤1 y ≤3 días, y las dos señales de presión operativa ya
identificadas (2019-12, 2021-05), son idénticos o casi idénticos bajo
ambos cortes. Lo que sí cambia de forma visible son los indicadores
que dependen de qué tan "maduros" se consideran los meses más
recientes del extracto: los KPI de cohorte madura de
`vw_report_cohorts` para 2022-10 y 2022-11 (menos reportes de esos
meses alcanzan el umbral de observación de 30 días bajo el corte más
temprano, así que su denominador madurado se reduce, y en 2022-11 deja
de haber ningún reporte maduro a 30 días bajo el corte corregido) y,
en menor medida, el Kaplan-Meier/CIF general a 7 y 30 días (cambios de
decenas de centésimas de punto porcentual). Ningún hallazgo de
`outputs/FINAL_FINDINGS.md` depende de los meses 2022-10/2022-11 como
evidencia aislada. El detalle numérico completo (antes/después, por
archivo) está en `CHANGELOG.md`.

## Regla de integridad (aplicada durante todo el proyecto)

- El archivo fuente permanece intacto en `data/raw/`; nunca se edita
  manualmente ni el pipeline lo sobrescribe.
- No se inventan filas, columnas ni estadísticas.
- No se presenta un dataset agregado de terceros (por ejemplo, el CSV
  agregado por alcaldía que cita el estudio de PLOS ONE en GitHub:
  `github.com/danielvelaguil/Missing-people`) como sustituto de la
  fuente caso-a-caso. Ese CSV se usó únicamente para verificar
  estructura histórica durante la investigación previa (ver
  `RESEARCH_LOG.md`); nunca fue insumo de los KPI de este proyecto.

## Si se consigue una versión más reciente del registro

El pipeline está diseñado para aceptar cualquier extracto con estas
columnas (`src/ingest.py::ALIASES`) sin cambios de código: basta con
colocar el nuevo archivo en `data/raw/` (dejando solo uno) y volver a
correr `python -m src.run_all`. Antes de comparar resultados entre
versiones, repetir la verificación de cobertura de esta página
(rango real de `report_date`, número de filas/columnas) para no asumir
que dos extractos cubren el mismo periodo.
