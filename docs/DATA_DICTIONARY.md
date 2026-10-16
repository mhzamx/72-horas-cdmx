# Diccionario de datos

Fuente: `data/raw/registro-interno-cbp-15-noviembre.xlsx` — Comisión de
Búsqueda de Personas de la Ciudad de México (CBPCDMX), Versión Pública del
Registro Interno de Personas Desaparecidas.

**2,958 filas × 21 columnas originales.** Cobertura real verificada:
`report_date` (fecha de reporte) va del **2019-06-25 al 2022-11-14**. Esta es
la fecha de corte que da nombre al archivo ("15 noviembre"), no la fecha
30/06/2023 que aparece en la página oficial actual ni el corte 2019–2023
de 3,450 registros usado en el estudio de PLOS ONE (Aguilar-Velázquez et
al., 2025) — ver `docs/SOURCE_ACCESS.md`. Es un extracto oficial más
antiguo del mismo registro, no un archivo distinto o de otra fuente.

Ningún archivo en `data/raw/` se modifica. Todo lo que sigue describe la
capa "cleaned" que produce `src/ingest.py` (tipos correctos, placeholders
normalizados) y la capa "analytical" que agregan las vistas SQL.

## Columnas originales → canónicas

| # | Columna original (xlsx) | Nombre canónico | Tipo | Nulos (n / %) | Ejemplo | Advertencias |
|---|---|---|---|---|---|---|
| 1 | `ID` | `source_id` | entero | 0 / 0% | 1954 | Identificador interno del archivo. Único (2,958 valores distintos). No es el folio oficial de la Comisión. |
| 2 | `Fecha.de.reporte.en.la.CBPCDMX` | `report_date` | fecha | 0 / 0% | 2022-11-14 | Único campo sin nulos. Formato original DD/MM/AAAA. |
| 3 | `Fuente.de.reporte` | `report_source` | categoría | 12 / 0.4% | NOTICIA / REPORTE | Solo dos valores útiles: `NOTICIA` (2,027) y `REPORTE` (919). |
| 4 | `Sexo` | `sex` | categoría | 12 / 0.4% | HOMBRE / MUJER | Sin categoría no binaria en este extracto. |
| 5 | `Edad` | `age` | entero (años) | 78 / 2.6% | 34 | Rango 0–98. 5 casos con edad 0 (posiblemente lactantes; no se asume error). No es un grupo/rango: el "grupo de edad" de la fuente académica es una variable **derivada** que este proyecto también calcula, ver `age_group`. |
| 6 | `Lugar.de.nacimiento` | `birthplace` | categoría | 1,971 / 66.6% | CIUDAD DE MEXICO | Alta tasa de nulos; no se usa en KPI. |
| 7 | `Nacionalidad` | `nationality` | categoría | 1,186 / 40.1% | MEXICANA | `MEXICANA` 1,641, `EXTRANJERA` 79, resto nulo o `S/D` (normalizado a nulo). |
| 8 | `Escolaridad` | `education` | categoría | 1,386 / 46.9% | SECUNDARIA | No se usa en KPI; documentado por completitud. |
| 9 | `Estado.civil` | `marital_status` | categoría | 2,350 / 79.4% | SOLTERO(A) | Muy incompleto; no se usa en KPI. |
| 10 | `Fecha.de.desaparicion` | `missing_date` | fecha | 53 / 1.8% | 2022-11-04 | Incluye 77 casos con fecha anterior a 2009 (ver `historic_missing_date`, no es error). |
| 11 | `Entidad.de.desaparicion` | `state_missing` | categoría | 196 / 6.6% | CIUDAD DE MEXICO | 2,718 casos en CDMX; 21 `S/D`; 15 `MEXICO` y unos pocos en otros estados (GUERRERO, VERACRUZ, JALISCO, etc.) — la Comisión también registra casos con algún vínculo a la Ciudad de México aunque los hechos hayan ocurrido en otra entidad. |
| 12 | `Municipio.Alcadia.de.la.desaparicion` | `borough_missing` | categoría | 196 / 6.6% (+32 placeholders → 228 / 7.7% sin alcaldía usable) | IZTAPALAPA | Nombre original mal escrito ("Alcadia"), se conserva tal cual como referencia. Placeholders `S/D`, `S/D/` (typo) y `SE DESCONOCE` se normalizan a nulo. `OTRO` (22 casos) y `NAUCALPAN DE JUAREZ` (2 casos, fuera de CDMX) se conservan como categorías propias — ver nota metodológica abajo. |
| 13 | `Colonia.de.la.desaparicion` | `colonia_missing` | texto libre | 1,744 / 59.0% | — | No se usa en KPI (texto libre, alta cardinalidad). |
| 14 | `Circunstancias.de.la.desaparicion` | `disappearance_circumstances` | texto libre | 219 / 7.4% | — | No se usa en KPI cuantitativos; posible insumo cualitativo futuro. |
| 15 | `Estatus.DESAPARECIDO` | `status` | categoría | 0 / 0% | LOCALIZADO / DESAPARECIDO | Solo dos valores en este extracto. Ver `is_located` para cómo se deriva el indicador binario. |
| 16 | `Condicion.localizacion` | `location_condition` | categoría | 1,199 / 40.5% | CON VIDA | `CON VIDA` 1,612, `SIN VIDA` 147. Nulo cuando no está localizado o cuando el dato no se capturó. |
| 17 | `Fecha.de.localizacion` | `location_date` | fecha | 1,379 / 46.6% (+29 con placeholder `"/  /"` → 1,408 / 47.6% sin fecha usable) | 2022-11-10 | El texto `"/  /"` es un placeholder de captura (fecha en blanco tecleada como plantilla vacía), no una fecha real; se trata igual que un nulo. |
| 18 | `Estado.de.Salud` | `health_status` | categoría | 2,418 / 81.7% | BUEN ESTADO | Solo se captura para localizados; alta tasa de nulos incluso entre ellos. |
| 19 | `Municipio.Alcaldia.de.la.localizacion` | `borough_location` | categoría | 2,713 / 91.7% | CUAUHTEMOC | Solo se llena para localizados (aun así, incompleto). Incluye municipios fuera de CDMX (Ecatepec, Nezahualcóyotl, etc.): la localización sí puede ocurrir fuera de la ciudad. |
| 20 | `Tipo.de.lugar.de.la.localizacion` | `location_place_type` | categoría | 2,015 / 68.1% | EN SU PROPIO DOMICILIO | Catálogo amplio con variantes de captura libre; no se normaliza en este proyecto. |
| 21 | `Motivo.referido.de.desaparicion` | `disappearance_reason` | texto libre | 2,387 / 80.7% | — | No se usa en KPI. |

**Nota sobre `state_location` (entidad de localización):** el archivo
**no incluye** una columna de entidad/estado para la localización, solo
`borough_location` a nivel municipio/alcaldía. La versión de 3,450
registros usada en el estudio de PLOS ONE sí reporta una novena variable
de "entidad de localización"; este extracto (más antiguo, 2,958 filas) no
la trae. Se documenta como ausente, no se inventa.

## Columnas derivadas (no vienen así en el archivo fuente)

| Columna | Cómo se calcula | Por qué |
|---|---|---|
| `case_key` | Correlativo 1..N asignado por el pipeline | Clave técnica estable dentro de una corrida; no es un folio oficial. |
| `age_group` | `age` agrupada en bins `0-11`, `12-17`, `18-29`, `30-44`, `45-59`, `60+` | Corte propio del proyecto (no viene en el archivo). Se separan niñez y adolescencia porque son categorías con dinámicas de búsqueda distintas. |
| `is_located` | 1 si `status` = `LOCALIZADO` | Indicador binario para KPI. |
| `event_to_report_days` / `_hours` | `report_date - missing_date`, solo si `report_date >= missing_date` | Tiempo hechos → reporte. |
| `report_to_location_days` / `_hours` | `location_date - report_date`, solo si `location_date >= report_date` | Tiempo reporte → localización (núcleo de "72 horas"). |
| `missing_to_location_days` | `location_date - missing_date`, solo si `location_date >= missing_date` | Tiempo desaparición → localización (línea de tiempo alterna, ver METHODOLOGY.md). |
| `valid_for_report_timeline` / `valid_for_missing_timeline` | Ver `sql/02_views.sql` | Definen la población analítica de cada línea de tiempo. |
| `excluded_from_report_timeline_reason` | Ver `sql/02_views.sql` | Explica, caso por caso, por qué un localizado no tiene duración válida desde el reporte. |

## Nota metodológica: `OTRO` vs. placeholders de "sin dato"

`S/D`, `S/D/` (variante con typo) y `SE DESCONOCE` se normalizan a nulo
porque significan explícitamente "no se capturó el dato". `OTRO` **se
conserva como categoría propia**: puede significar "un lugar real que no
está en el catálogo de 16 alcaldías", que es información distinta a "no
sé". Tratarlo como nulo habría borrado esa distinción; tratarlo como una
17ª alcaldía real habría sido engañoso. Se muestra en las tablas con su
propio renglón y, al tener menos de 30 casos, queda excluido de gráficos
comparativos por tamaño de muestra insuficiente (no por ser inválido).

## Ver también

- `docs/METHODOLOGY.md` — cómo se usan estas columnas para definir la
  población de cada análisis y por qué hay dos relojes distintos.
- `sql/02_views.sql` — implementación exacta de cada columna derivada.
- `outputs/tables/data_quality_summary.csv` — conteo exacto de cada
  regla de calidad sobre la corrida más reciente.
