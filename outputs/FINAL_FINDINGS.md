# Hallazgos finales — 72 HORAS

Generado a partir de `data/raw/registro-interno-cbp-15-noviembre.xlsx`
(CBPCDMX, Versión Pública del Registro Interno de Personas Desaparecidas).
**Cobertura real: reportes del 2019-06-25 al 2022-11-14** (2,958 casos).
Ver `docs/DATA_DICTIONARY.md` y `docs/SOURCE_ACCESS.md` para el detalle
de por qué esta ventana difiere de otras versiones documentadas del
mismo registro.

Todos los números de este documento salen directamente de
`outputs/tables/*.csv`, regenerables con `python -m src.run_all`.
Metodología completa en `docs/METHODOLOGY.md`.

## 1. Panorama general

- **2,958** reportes en la ventana observada.
- **1,777** (60.1%) tenían estatus `LOCALIZADO` al corte del extracto;
  **1,181** (39.9%) seguían como `DESAPARECIDO`.
- De los 1,777 localizados, **1,213** tienen una duración reporte→localización
  calculable de forma limpia; los otros **564** quedan fuera de ese
  cálculo específico por alguna de estas razones documentadas: 227 no
  tienen fecha de localización utilizable pese al estatus, y 337 tienen
  una fecha de localización anterior a la del reporte (318 clasificados
  AMBIGUOUS — de ellos, 315 con `missing_date` conocida y
  `location_date` posterior a la desaparición, y 3 con `missing_date`
  faltante, sin forma de determinar el orden — y 19 clasificados
  IMPOSSIBLE por tener `location_date` anterior a la propia
  desaparición; ver sección 3).

## 2. La pregunta central: 72 horas — dos respuestas, no una

**(A) Entre los casos ya localizados** (n=1,213), el **67.1%** se
localizó en ≤3 días desde el reporte. La mediana es de solo **1 día**
(P75 = 6 días, P90 = 18.8 días, P95 = 51.2 días): la mayoría de los
casos que se resuelven, se resuelven rápido, pero una cola larga de
casos tarda mucho más — por eso el promedio (15.0 días) es engañoso
frente a la mediana.

**(B) Considerando también los casos aún abiertos** (n=2,394 en riesgo,
vía Kaplan-Meier), la estimación de "% ya localizado a los 3 días" cae a
**34.0%**. A 7 días: 40.4%. A 30 días: 47.4%.

La diferencia entre (A) 67.1% y (B) 34.0% —33 puntos— **no es un error
de cálculo**: es el efecto exacto de que casi 4 de cada 10 reportes de
este extracto seguían sin localización al momento del corte, y (A) los
excluye del cálculo por construcción. Cuando se hable de "qué tan rápido
localiza el sistema", la cifra honesta es la de Kaplan-Meier (B), no la
cifra entre-localizados (A). Ambas se reportan porque responden
preguntas distintas y legítimas.

| Umbral | (A) % entre localizados | (B) % estimado del total (Kaplan-Meier) |
|---|---|---|
| ≤1 día | 52.3% | 26.5% |
| ≤3 días | 67.1% | 34.0% |
| ≤7 días | 79.5% | 40.4% |
| ≤30 días | 93.1% | 47.4% |

## 3. Localizados "antes del reporte": un patrón real, no un error masivo

337 casos (11.4% del total) tienen `location_date < report_date`. Al
revisarlos contra `missing_date`, se dividen en tres grupos, no dos:
**315** tienen `missing_date` conocida y una localización posterior a
la propia desaparición — consistentes con que la persona fue
encontrada antes de que el reporte quedara formalmente registrado en
el sistema de la Comisión; **3** tienen `missing_date` faltante, así
que no se puede determinar el orden real (no se les asume ningún
orden, se agrupan por defecto con los anteriores: **318** en total
clasificados AMBIGUOUS, no como error); y **19** (0.6% del total)
tienen una localización anterior incluso a la desaparición, lo que sí
es un orden lógicamente imposible y se documenta como error de
captura — clasificados IMPOSSIBLE. Tratar los 337 como "error" habría
sido incorrecto.

Por separado, existe un chequeo global de `location_date < missing_date`
sobre **todo** el dataset (no solo sobre estos 337): da **21** casos.
De ellos, 19 coinciden con los IMPOSSIBLE de arriba; los **2** restantes
tienen `location_date >= report_date` (por eso no forman parte de los
337 de esta sección) pero igual tienen `location_date < missing_date`
— casos con `missing_date` inusualmente tardía respecto al reporte y a
la localización, documentados como parte del mismo patrón de calidad
en `docs/METHODOLOGY.md` §5, sin que cambien la clasificación analítica
de los 337 de aquí.

## 4. Diferencias por alcaldía (n analítico ≥30, entre localizados)

**Nota sobre las dos N de esta sección.** Cada porcentaje tiene dos
tamaños de muestra distintos y ambos importan: **N total** es cuántos
reportes tiene esa alcaldía en total (`sample_size` en
`borough_kpis.csv`); **n analítico** es cuántos de esos reportes
entran realmente en el cálculo del porcentaje — están localizados y
tienen una duración reporte→localización limpia
(`located_with_valid_duration`, el mismo denominador de
`pct_located_le_3d_among_located`). N total siempre es ≥ n analítico
porque excluye a los casos aún abiertos y a los que quedan fuera del
cálculo por alguna razón documentada en §1 y §3. **El umbral mínimo de
30 casos que decide qué alcaldía entra en esta comparación se aplica
sobre n analítico**, no sobre N total — porque n analítico es el
verdadero denominador del porcentaje que se está comparando.

Rango observado (alcaldías con n analítico ≥30, ordenadas de mayor a
menor % en ≤3 días):

| Alcaldía | % ≤3 días | N total | n analítico |
|---|---|---|---|
| Miguel Hidalgo | 78.9% | 122 | 52 |
| Benito Juárez | 72.9% | 145 | 70 |
| Cuauhtémoc | 70.8% | 366 | 171 |
| Gustavo A. Madero | 70.7% | 328 | 123 |
| Tláhuac | 70.3% | 113 | 64 |
| Iztacalco | 70.0% | 86 | 40 |
| Venustiano Carranza | 69.6% | 170 | 69 |
| Tlalpan | 68.1% | 156 | 72 |
| Azcapotzalco | 67.3% | 153 | 55 |
| Coyoacán | 66.3% | 166 | 83 |
| Xochimilco | 64.2% | 134 | 53 |
| Iztapalapa | 61.6% | 452 | 185 |
| Álvaro Obregón | 61.5% | 193 | 83 |

Rango observado: de **61.5%** (Álvaro Obregón, n analítico=83) a
**78.9%** (Miguel Hidalgo, n analítico=52) localizado en ≤3 días.
Iztapalapa, la alcaldía con más volumen (N total=452, n analítico=185),
está en el rango bajo (61.6%) y tiene uno de los tiempos promedio más
altos (25.3 días) — combinación de alto volumen y resolución más lenta
que vale la pena señalar, sin atribuir causa.

**Corrección aplicada en esta revisión.** Cuajimalpa de Morelos (N
total=54, n analítico=23) y La Magdalena Contreras (N total=47, n
analítico=20) ya no entran en esta comparación: en la versión anterior
de este documento el umbral de 30 se aplicaba sobre N total, así que
ambas pasaban el filtro aunque su porcentaje (60.9% y 55.0%
respectivamente) en realidad se calculaba sobre menos de 30 casos
localizados con duración válida. Esto movió el extremo bajo del rango:
antes se citaba 55.0% (La Magdalena Contreras) como mínimo; con el
denominador real como criterio, el mínimo pasa a ser 61.5% (Álvaro
Obregón). Ninguna cifra de la tabla cambió — solo cambió qué alcaldías
son comparables con esta N. Junto con Otro, Milpa Alta y Naucalpan de
Juárez, Cuajimalpa de Morelos y La Magdalena Contreras quedan fuera de
esta tabla pero siguen visibles en `outputs/tables/borough_kpis.csv`
(marcadas con `below_min_sample_size=1`) para no ocultar esos casos.

## 5. Sexo: sin diferencia relevante

67.5% (hombres, N total=1,856, n analítico=692) vs. 66.2% (mujeres,
N total=1,090, n analítico=515) localizado en ≤3 días entre
localizados. Una diferencia de 1.3 puntos porcentuales con estas N no
se interpreta como un hallazgo. (n analítico = `located_with_valid_duration`
en `outputs/tables/sex_kpis.csv`; ambos grupos están muy por encima del
umbral mínimo de 30.)

## 6. Grupo de edad: gradiente por edad

| Grupo de edad | % ≤3 días | N total | n analítico |
|---|---|---|---|
| 0-11 | 64.2% | 137 | 53 |
| 12-17 | 62.7% | 491 | 260 |
| 18-29 | 68.0% | 751 | 319 |
| 30-44 | 64.6% | 724 | 268 |
| 45-59 | 70.1% | 423 | 147 |
| 60+ | 72.5% | 354 | 149 |

De 62.7% (12-17 años, el grupo más bajo, N total=491, n analítico=260)
a 72.5% (60+ años, el más alto, N total=354, n analítico=149). El grupo
de adolescentes (12-17) tiene la segunda mayor cantidad de casos y una
de las tasas de resolución rápida más bajas — un patrón que merece
investigación cualitativa adicional (por ejemplo, si hay diferencias en
el tipo de caso), no una conclusión causal a partir de este dato
agregado. Todos los grupos de edad están muy por encima del umbral
mínimo de 30 tanto en N total como en n analítico — a diferencia de
alcaldía (§4), aquí el umbral aplicado sobre n analítico no excluye a
ningún grupo adicional.

## 7. Evolución temporal y señales de presión operativa

Se identificaron **2 meses** (2019-12 y 2021-05) donde coinciden un
volumen de reportes anormalmente alto (z-score ≥2 frente a los 12 meses
reales previos) con un deterioro del % de localización en ≤3 días
frente a su propia tendencia reciente de 6 meses. Ambos caen dentro de
la ventana real de reportes (2019-06 a 2022-11). Es una señal
descriptiva para priorizar revisión, no una prueba de causalidad ni una
falla atribuible a alguna autoridad.

**Corrección aplicada en esta revisión: 2019-11 ya no es una señal.**
En la versión anterior de este documento se reportaban 3 meses,
incluyendo 2019-11. Al auditar la línea base de 12 meses usada para el
z-score de volumen de reportes, se encontró que arrastraba los 5 meses
de relleno anteriores a la ventana real (ver más abajo) como si fueran
meses reales con 0 reportes, inflando artificialmente el z-score de los
primeros meses de la ventana. Corregido para que la línea base solo
cuente meses reales dentro de `in_report_window=1` y exija el mínimo de
6 meses de historia real que el método siempre requirió:
- **2019-11** ya no tiene línea base suficiente (solo 5 meses reales de
  historia — 2019-06 a 2019-10 — por debajo del mínimo de 6): su
  z-score pasa a ser indeterminado (no se puede evaluar con este
  método) y por lo tanto deja de contarse como señal.
- **2019-12** sí alcanza el mínimo de 6 meses reales de historia
  (2019-06 a 2019-11) y su z-score corregido es **2.73** (antes,
  contaminado con meses de relleno, era 3.46) — sigue siendo ≥2 y sigue
  coincidiendo con una caída real en la resolución a 3 días (15.9% vs.
  30.5% de tendencia), así que **se mantiene como señal**.
- **2021-05** no se ve afectado (está muy lejos de los meses de
  relleno en la serie): se mantiene sin cambios, z=3.36.

## 8. Por qué la tabla de flujo mensual tiene 48 filas y no 42

La ventana de reportes
(2019-06-25 a 2022-11-14) cubre 42 meses calendario. Pero el eje de
meses de estas tablas (`vw_monthly_flow` en `sql/02_views.sql`) no es
solo "meses con reportes": es la unión de meses con **al menos un
reporte O al menos una localización**. Esto es intencional — si el eje
se limitara a meses de reporte, las localizaciones que caen fuera de
esa ventana desaparecerían silenciosamente de las columnas
`localizations` y `net_backlog_flow`, subestimando las resoluciones
reales. Esa unión agrega 6 meses adicionales (42 + 6 = 48):

- **5 meses anteriores a la ventana** (2011-11, 2012-04, 2017-04,
  2018-01, 2018-03): cada uno corresponde a exactamente 1 caso cuyo
  `location_date` es mucho más antiguo que el arranque del registro de
  reportes — backlog histórico, no un error de captura por sí solo
  (ver también `historic_missing_date` en §9, un patrón similar en
  `missing_date`).
- **1 mes posterior a la ventana** (2022-12): 1 caso reportado dentro
  de la ventana pero localizado un mes después del último reporte
  observado (2022-11-14) — perfectamente legítimo, no un error.

Los 6 meses "extra" tienen `reports=0` y `pressure_signal=0` — no
participan en la detección de presión operativa ni en ningún promedio
móvil más allá de aportar, correctamente, sus localizaciones a
`net_backlog_flow`. Se agregó una columna `in_report_window` a ambos
CSV (1 = dentro de 2019-06 a 2022-11, 0 = mes extra) para que esta
distinción sea explícita sin necesidad de leer el SQL. Ningún valor
numérico existente (reportes, localizaciones, z-scores, señales de
presión) cambió al agregar esta columna.

## 9. Calidad de datos: resumen

| Categoría | Regla | Casos | % |
|---|---|---|---|
| MISSING | Sin fecha de localización utilizable | 1,408 | 47.6% |
| MISMATCH | Estatus LOCALIZADO sin fecha de localización | 227 | 7.7% |
| MISSING | Sin alcaldía utilizable | 228 | 7.7% |
| AMBIGUOUS | Localización antes del reporte (no todos son error, ver §3) | 337 | 11.4% |
| OUTLIER | Desaparición de larga data (>10 años antes de la ventana) | 77 | 2.6% |
| MISSING | Sin fecha de desaparición | 53 | 1.8% |
| IMPOSSIBLE | Localización antes de la propia desaparición | 21 | 0.7% |
| IMPOSSIBLE | Reporte antes de la desaparición | 8 | 0.3% |
| DUPLICATE | Contenido idéntico salvo el ID | 16 (7 grupos) | 0.5% |

Ningún caso fue eliminado por estos flags; todos siguen en
`cases_raw` y se pueden auditar en `outputs/tables/data_quality_summary.csv`
y `outputs/tables/location_before_report_sample.csv`.

## 10. Qué NO dice este análisis

- No mide causalidad: ninguna diferencia entre alcaldías, sexos o
  grupos de edad implica que un factor específico *cause* mayor o menor
  velocidad de localización.
- No cubre el periodo posterior a noviembre de 2022 (ver el párrafo de
  cobertura al inicio del documento y `docs/SOURCE_ACCESS.md`).
- No equivale a la totalidad de personas desaparecidas de Ciudad de
  México en el RNPDNO nacional (ver `docs/ETHICS.md`, punto 6).
- No evalúa la calidad de la búsqueda en sí (diligencias realizadas),
  solo el tiempo observado entre fechas registradas.

---

# Ampliación: desenlaces CON VIDA / SIN VIDA

Todo lo que sigue (§11-§17) es una ampliación posterior del proyecto.
No cambia ni un solo número de las secciones 1-10 — es un análisis
adicional sobre una columna del archivo fuente (`Condicion.localizacion`
/ `location_condition`) que ya estaba mapeada pero no se usaba
analíticamente. Se generó con `src/outcomes.py`, pasos 11-13 de
`python -m src.run_all`.

**Advertencia que aplica a TODA esta ampliación, sin excepción:**
`location_date` es la fecha que el registro captura como fecha de
localización de la persona (ver `docs/DATA_DICTIONARY.md`) — **no es la
fecha de fallecimiento**. El archivo fuente no contiene ninguna columna
con la fecha de muerte, y tampoco documenta si `location_date`
corresponde al cierre administrativo del expediente o a otro momento
del proceso (esa equivalencia no tiene respaldo documental y no se
afirma aquí). Por lo tanto, nada de lo que sigue debe leerse como "la
persona murió en tal intervalo de tiempo", ni como "buscar más rápido
habría evitado la muerte". Lo único que se mide es la asociación entre
el tiempo hasta la fecha de localización registrada y el desenlace (CON
VIDA / SIN VIDA) capturado en esa misma fecha. Esta ampliación tampoco
es evidencia de que el proyecto esté "terminado": deja hallazgos
exploratorios y al menos una hipótesis sin dato para probarla (§17).

## 11. Auditoría de `location_condition`

De los 1,777 casos con estatus LOCALIZADO:

| Categoría | Casos |
|---|---|
| CON VIDA | 1,612 |
| SIN VIDA | 147 |
| Condición desconocida | 18 |
| **Total localizados** | **1,777** |

Las tres categorías suman exactamente el total — no hay fuga hacia
otras categorías ni pérdida de casos. Se verificó además, contra el
archivo crudo (no solo contra las vistas SQL), que **0 casos con
estatus DESAPARECIDO tienen `location_condition` no nula**: la columna
nunca aparece "adelantada" en un caso que sigue abierto.

Los 18 casos con condición desconocida se descomponen así:

- **9 casos** tienen fecha de localización utilizable pero la condición
  no se capturó — un vacío de captura sin más explicación disponible.
- **9 casos** no tienen ni fecha de localización ni condición — parte
  de los 227 "estatus LOCALIZADO sin fecha de localización utilizable"
  ya documentados en §9, en su versión más incompleta.

Adicionalmente, **218 casos** sí tienen `location_condition` capturada
pero NO tienen fecha de localización utilizable (el resto de los 227 de
§9: 227 = 218 + 9 recién mencionados). Es decir: sabemos si esa persona
fue encontrada con o sin vida, pero no en qué fecha exacta — por eso
estos 218 casos entran en las comparaciones por sexo/edad/alcaldía
(§13, que no exige fecha) pero NO entran en las tablas por intervalo de
tiempo ni en el modelo de riesgos competitivos (§12 y §14, que sí la
exigen). Esta distinción de denominadores se mantiene explícita en cada
tabla de aquí en adelante.

Ninguna inconsistencia real encontrada — solo datos faltantes,
documentados como tales. Fuente: `outputs/tables/outcome_audit.csv`.

## 12. Desenlace por intervalo de tiempo

Dos relojes, igual que en el resto del proyecto (§1-§2): desde el
**reporte** (pregunta central del proyecto) y desde la **desaparición**
(incluye los casos localizados antes del registro del reporte, ver §3).
Solo se incluyen localizados con duración válida en el reloj
correspondiente — los excluidos se documentan aparte.

**Reloj reporte → localización** (n=1,213 con duración válida — el
mismo 1,213 de §1 y §2 —, de los cuales 1,207 tienen además
`location_condition` conocida y 6 no; ver tabla de exclusiones abajo):

| Intervalo | CON VIDA | SIN VIDA | Desconocida | Total | % del intervalo que es SIN VIDA |
|---|---|---|---|---|---|
| ≤1 día | 599 | 34 | 1 | 634 | 5.4% |
| >1-3 días | 160 | 18 | 2 | 180 | 10.0% |
| >3-7 días | 136 | 12 | 2 | 150 | 8.0% |
| >7-30 días | 145 | 20 | 0 | 165 | 12.1% |
| >30 días | 67 | 16 | 1 | 84 | 19.0% |

Dentro de cada desenlace, cómo se reparte en el tiempo: de los 100 SIN
VIDA con duración válida, 34% se registró en ≤1 día, 18% en >1-3 días,
12% en >3-7 días, 20% en >7-30 días y 16% en >30 días. De los 1,107 CON
VIDA con duración válida, la concentración es mucho mayor en ≤1 día
(54.1%). Estas dos distribuciones ya insinúan lo que confirma el modelo
de riesgos competitivos en §14: el desenlace SIN VIDA se reparte de
forma más pareja a lo largo del tiempo, mientras que CON VIDA se
concentra fuertemente en las primeras horas.

**Exclusiones de este reloj** (localizados sin duración reporte→localización
válida, por razones ya documentadas en §1 y §3 — no son casos perdidos,
solo no entran en ESTA tabla): 505 CON VIDA, 47 SIN VIDA, 12 desconocida
(564 en total, el mismo número que en §1).

**Reloj desaparición → localización** (n=1,522 con duración válida —
incluye a los localizados antes del reporte, §3):

| Intervalo | CON VIDA | SIN VIDA | Desconocida | Total | % del intervalo que es SIN VIDA |
|---|---|---|---|---|---|
| ≤1 día | 368 | 18 | 1 | 387 | 4.7% |
| >1-3 días | 311 | 22 | 1 | 334 | 6.6% |
| >3-7 días | 261 | 22 | 2 | 285 | 7.7% |
| >7-30 días | 296 | 36 | 3 | 335 | 10.7% |
| >30 días | 156 | 23 | 2 | 181 | 12.7% |

Exclusiones de este reloj: 220 CON VIDA, 26 SIN VIDA, 9 desconocida (255
en total).

**Descripción fiel del patrón (corregida):** bajo el reloj
desaparición→localización, la fracción SIN VIDA del intervalo sí crece
en cada paso sin excepción (4.7% → 6.6% → 7.7% → 10.7% → 12.7%). Bajo
el reloj reporte→localización, la tendencia general también es de
intervalos cortos hacia largos con menor a mayor proporción SIN VIDA,
pero **no en cada intervalo**: hay una caída de >1-3 días (10.0%) a
>3-7 días (8.0%) antes de volver a subir en >7-30 días (12.1%) y >30
días (19.0%). No se debe afirmar "crece conforme crece el tiempo,
nunca al revés" como si fuera válido en cada tramo bajo ambos relojes
— eso solo es cierto para el reloj desaparición→localización. Con los
conteos de esta tabla (12 y 18 casos SIN VIDA en los tramos >3-7 y
>1-3 días del reloj reporte), la caída puede deberse a variación
esperable con muestras de este tamaño, no necesariamente a un patrón
real distinto entre relojes. De cualquier forma, esto es una asociación
temporal, no una prueba de que el tiempo cause el desenlace: personas
con circunstancias más graves desde el inicio también podrían tardar
más en resolverse por razones ajenas al tiempo en sí (ver §16).

Fuentes: `outputs/tables/outcome_intervals_report_clock.csv`,
`outcome_intervals_missing_clock.csv`, `outcome_intervals_exclusions.csv`.

## 13. Diferencias por sexo, edad y alcaldía

Denominador de esta sección: localizados con `location_condition`
conocida (CON VIDA o SIN VIDA), **sin exigir además duración válida**
(a diferencia de §12) — por eso el n analítico aquí es distinto al de
las tablas de velocidad (§4-§6) y al de §12. Es intencional: aquí la
pregunta es "de los que sabemos su desenlace, ¿varía por grupo?", no
"¿cuándo ocurre en el tiempo?". Intervalo de confianza: Wilson al 95%,
más confiable que el normal simple con proporciones bajas como SIN VIDA
(mayoritariamente entre 1% y 14% aquí). Umbral N≥30 aplicado sobre este
n analítico, igual criterio que ya se corrigió para las tablas de
velocidad.

**Por sexo** (ambos muy por encima de N≥30):

| Sexo | n analítico | SIN VIDA | % SIN VIDA | IC 95% |
|---|---|---|---|---|
| Hombre | 1,026 | 111 | 10.8% | [9.1%, 12.9%] |
| Mujer | 724 | 35 | 4.8% | [3.5%, 6.6%] |

Los intervalos de confianza NO se traslapan: con esta muestra, la
diferencia entre hombres y mujeres en la proporción de desenlace SIN
VIDA es estadísticamente clara. Esto es una diferencia observada, no
una explicación — no dice por qué, y de ningún modo implica que el
sexo *cause* el desenlace.

**Por grupo de edad** (todos por encima de N≥30):

| Grupo de edad | n analítico | SIN VIDA | % SIN VIDA | IC 95% |
|---|---|---|---|---|
| 45-59 | 216 | 27 | 12.5% | [8.7%, 17.6%] |
| 30-44 | 397 | 45 | 11.3% | [8.6%, 14.8%] |
| 60+ | 248 | 28 | 11.3% | [7.9%, 15.8%] |
| 18-29 | 453 | 38 | 8.4% | [6.2%, 11.3%] |
| 12-17 | 343 | 8 | 2.3% | [1.2%, 4.5%] |
| 0-11 | 75 | 1 | 1.3% | [0.2%, 7.2%] |

**No hay un gradiente continuo con la edad** — se verificó el
traslape de los 15 pares posibles de intervalos de confianza y el
patrón real es un escalón, no una rampa: 12-17 años tiene una
proporción de SIN VIDA claramente menor y su IC no se traslapa con
NINGUNO de los cuatro grupos de 18 años en adelante (18-29, 30-44,
45-59, 60+). Los cuatro grupos adultos, en cambio, se traslapan todos
entre sí — incluido 18-29 (8.4%) con los tres de mayor edad — así que
no hay evidencia de una diferencia real *dentro* de la población adulta,
y en particular **60+ (11.3%) no es más alto que 45-59 (12.5%)**: no
crece de forma continua con la edad, se estabiliza. 0-11 tiene apenas 1
caso SIN VIDA, por lo que su IC es muy ancho ([0.2%, 7.2%]) — tan ancho
que, a pesar de que su porcentaje puntual (1.3%) es el más bajo de la
tabla, su intervalo SÍ se traslapa con el de 18-29 ([6.2%, 11.3%]): no
hay evidencia estadística de que 0-11 difiera de 18-29, aunque sí la
hay de que difiere de los tres grupos de mayor edad (30-44, 45-59, 60+).
No se debe leer "1.3%" como una cifra precisa ni generalizar "los
menores de edad son categóricamente distintos de todos los adultos".

**Por alcaldía** (N≥30; quedan fuera Cuajimalpa de Morelos n=29, Milpa
Alta n=10, Otro n=14 y Naucalpan de Juárez n=1 — nótese que el n
analítico aquí no es el mismo que en §4, así que una alcaldía puede
calificar aquí y no allá, o viceversa; ver más abajo):

| Alcaldía | n analítico | SIN VIDA | % SIN VIDA | IC 95% |
|---|---|---|---|---|
| Miguel Hidalgo | 75 | 10 | 13.3% | [7.4%, 22.8%] |
| Benito Juárez | 100 | 11 | 11.0% | [6.3%, 18.6%] |
| Cuauhtémoc | 221 | 24 | 10.9% | [7.4%, 15.7%] |
| Xochimilco | 81 | 8 | 9.9% | [5.1%, 18.3%] |
| Iztacalco | 55 | 5 | 9.1% | [4.0%, 19.6%] |
| Azcapotzalco | 91 | 8 | 8.8% | [4.5%, 16.4%] |
| Tláhuac | 70 | 6 | 8.6% | [4.0%, 17.5%] |
| Tlalpan | 104 | 8 | 7.7% | [4.0%, 14.5%] |
| Álvaro Obregón | 119 | 9 | 7.6% | [4.0%, 13.8%] |
| Coyoacán | 117 | 8 | 6.8% | [3.5%, 12.9%] |
| Iztapalapa | 281 | 19 | 6.8% | [4.4%, 10.3%] |
| La Magdalena Contreras | 30 | 2 | 6.7% | [1.9%, 21.3%] |
| Venustiano Carranza | 99 | 6 | 6.1% | [2.8%, 12.6%] |
| Gustavo A. Madero | 186 | 11 | 5.9% | [3.3%, 10.3%] |

**Por qué La Magdalena Contreras aparece aquí (n=30) pero no en §4
(n analítico de velocidad=20):** en §4 el denominador exige duración
reporte→localización válida; aquí el denominador solo exige conocer
`location_condition`, que existe en más casos de los que tienen fecha
utilizable (ver §11). No es una inconsistencia — son dos preguntas
distintas con dos poblaciones distintas, ambas documentadas.

Se verificaron los 91 pares posibles entre las 14 alcaldías con N≥30:
**ninguno** de los 91 pares tiene intervalos de confianza disjuntos —
no es solo que los extremos (Gustavo A. Madero [3.3%, 10.3%] y Miguel
Hidalgo [7.4%, 22.8%]) se crucen, es que se traslapan absolutamente
todos entre sí. **Con este tamaño de muestra no hay evidencia de que la
alcaldía en sí distinga el
desenlace** — a diferencia de sexo y edad, donde sí hay intervalos que
no se traslapan. Esto no significa que no haya diferencia real; puede
haberla y esta muestra no ser lo bastante grande para detectarla, o el
factor real puede estar correlacionado con otra variable no controlada
aquí (edad, tipo de circunstancia). No se presenta ningún ranking de
alcaldías por este indicador como si fuera un hallazgo firme.

Fuentes: `outputs/tables/outcome_by_sex.csv`, `outcome_by_age_group.csv`,
`outcome_by_borough.csv`.

## 14. Método correcto: riesgos competitivos, no Kaplan-Meier simple

**Por qué no se reutilizó el Kaplan-Meier de §2.** Ese modelo trata
"estar localizado" como un único evento. Con dos desenlaces que compiten
por el mismo caso (CON VIDA, SIN VIDA), medir SIN VIDA con un
Kaplan-Meier simple — tratando CON VIDA y los casos abiertos como si
fueran censura — sobreestima la incidencia de SIN VIDA: ignora que el
desenlace CON VIDA retira población en riesgo por una razón distinta a
la censura. El estimador correcto para desenlaces que compiten es la
función de incidencia acumulada de Aalen-Johansen.

**Corrección de la revisión anterior (ver `CHANGELOG.md` para el
detalle completo).** La primera versión de este cálculo usaba
`lifelines.AalenJohansenFitter`, que resuelve los tiempos empatados con
un jitter aleatorio continuo (la propia librería emite una advertencia
sobre esto). Con datos en días enteros y cientos de casos localizados
el mismo día (día 0 o día 1), ese jitter desplazaba una fracción real
de esos casos a un lado u otro de umbrales enteros como "≤1 día" —
verificado: a ≤1 día, CON VIDA daba 20.6% con jitter vs. **25.0% con el
cálculo exacto**, una diferencia de ~4.4 puntos causada por el jitter,
no por los datos. Se reemplazó ese cálculo por un estimador exacto
(Kalbfleisch & Prentice 1980) que agrega los empates en vez de
romperlos con aleatoriedad — sin semilla, sin jitter, determinista. En
esa revisión se verificó contra un cálculo externo hecho sobre los
datos crudos, bajo el corte administrativo vigente en ese momento
(2022-12-15): a ≤3 días, CON VIDA 31.70426% y SIN VIDA 2.17210% —
coincidencia a 5 decimales. También se añadieron pruebas
(`tests/test_outcomes.py`) con eventos sintéticos empatados
exactamente en los días 1, 3, 7 y 30, confirmando que el umbral es
inclusivo del día exacto.

**Corrección adicional de esta revisión (auditoría de la fecha de
corte, ver `docs/METHODOLOGY.md` §7.1 y `CHANGELOG.md`).** Al corregir el corte
administrativo de 2022-12-15 a 2022-11-15 (un solo registro atípico,
ID 1138, inflaba el corte anterior en un mes), una prueba de
regresión que hasta entonces siempre había pasado empezó a fallar: la
identidad "suma de las CIF de todos los desenlaces = Kaplan-Meier de
cualquier evento" dejó de cumplirse exactamente. La causa era un
segundo defecto, independiente del jitter y presente desde la revisión
anterior, en la fórmula de supervivencia de `_competing_risk_cif`:
restaba del riesgo tanto los eventos reales como las salidas por
censura en el mismo paso, cuando solo los eventos reales deben
reducirla (la censura ya se refleja al reducir el denominador del paso
siguiente). Era matemáticamente detectable con un ejemplo mínimo
(duraciones `1,1,2,3`; eventos `evento, censurado-empatado-en-el-día-1,
evento, censurado`: la versión con el error da 0.5 acumulado al día 2,
la correcta da 0.625 — idéntico a `lifelines.KaplanMeierFitter` sobre
el mismo ejemplo), pero permanecía invisible bajo el corte anterior
porque ningún caso censurado tenía entonces una duración corta que
empatara con un evento real en los primeros días; la corrección del
corte, al traer casos censurados con duraciones más cortas, hizo visible
un error que ya existía. Se corrigió la fórmula y se añadió
`test_cif_handles_censoring_tied_with_an_event_on_the_same_day` como
prueba de regresión permanente (25/25 pruebas pasan tras la corrección).

Consecuencia honesta para las cifras: los valores 31.70426%/2.17210%
verificados en la revisión anterior contra la referencia externa **ya
no describen la población actual** — cambiaron ligeramente (a
31.71869%/2.17374%) porque el corte y la fórmula cambiaron, no porque
el método vuelva a estar en duda. La verificación disponible sobre los
datos ya corregidos no es esa referencia externa puntual (calculada
bajo un corte que este mismo proceso determinó que era incorrecto),
sino la identidad matemática interna, que sí se sigue cumpliendo
exactamente (ver el detalle más abajo).

Se calcularon ambos métodos —ingenuo y correcto— para dejar medida la
magnitud real del sesgo, no para usar el ingenuo en ningún hallazgo.
Cifras vigentes tras ambas correcciones de esta revisión (cutoff +
fórmula):

| Umbral | Desenlace | Método ingenuo (KM simple, mal usado) | Aalen-Johansen (correcto, exacto) | Sobreestimación |
|---|---|---|---|---|
| ≤1 día | CON VIDA | 25.13% | 25.02% | +0.43% |
| ≤3 días | CON VIDA | 31.97% | 31.72% | +0.79% |
| ≤7 días | CON VIDA | 37.91% | 37.46% | +1.20% |
| ≤30 días | CON VIDA | 44.43% | 43.68% | +1.72% |
| ≤1 día | SIN VIDA | 1.50% | 1.42% | +5.49% |
| ≤3 días | SIN VIDA | 2.53% | 2.17% | +16.52% |
| ≤7 días | SIN VIDA | 3.31% | 2.68% | +23.45% |
| ≤30 días | SIN VIDA | 4.77% | 3.54% | +34.85% |

**Esto corrige la caracterización anterior del sesgo.** No es un sesgo
"sistemático y parejo": para CON VIDA (el desenlace mayoritario) el
método ingenuo apenas sobreestima (menos de 2 puntos porcentuales en
todos los umbrales); para SIN VIDA (el desenlace minoritario) la
sobreestimación sí crece con el horizonte de tiempo y llega a ser
considerable a 30 días (+34.5%). El sesgo del método ingenuo es real,
pero mucho más pronunciado en el desenlace minoritario que en el
mayoritario — no una distorsión uniforme como se afirmó antes.

**Corrección adicional de esta revisión (consistencia del corte con
`location_date`, ver `docs/METHODOLOGY.md` §7.1 y `CHANGELOG.md`).**
Un `location_date` **posterior** al corte administrativo no puede
tratarse como un evento observado — esa información no existiría
todavía "al momento del corte". El caso ID 1138, con `location_date`
2022-12-15 (posterior al corte 2022-11-15), se contaba antes como
evento CON VIDA observado a los 464 días; se re-censura ahora al corte
(pasa a contar como abierto, con duración ≈434 días). Es el único caso
del extracto con esta condición. Efecto en las cifras de abajo:
**ninguno** en los umbrales ≤1/≤3/≤7/≤30 días (su duración excede los
30 días bajo cualquiera de las dos interpretaciones), pero sí cambia el
recuento de población (1,106 CON VIDA en vez de 1,107; 1,182 abiertos
en vez de 1,181) y, en la cola de la curva completa
(`outcome_cif_curve_con_vida.csv`, día ≥434), la CIF final de CON VIDA
baja de 47.11% a 47.04%.

**Resultado correcto**, sobre la misma población que el Kaplan-Meier
general (2,394 casos en riesgo: 1,182 aún abiertos, 1,106 CON VIDA, 100
SIN VIDA, 6 con condición desconocida):

| Umbral | % CON VIDA (Aalen-Johansen) | % SIN VIDA (Aalen-Johansen) | % DESCONOCIDA (Aalen-Johansen) | % S(t): aún sin ningún evento |
|---|---|---|---|---|
| ≤1 día | 25.02% | 1.42% | 0.04% | 73.52% |
| ≤3 días | 31.72% | 2.17% | 0.13% | 65.98% |
| ≤7 días | 37.46% | 2.68% | 0.21% | 59.65% |
| ≤30 días | 43.68% | 3.54% | 0.21% | 52.57% |

**Corrección de esta revisión sobre la descripción de la última
columna.** Una versión anterior de esta tabla llamaba a la última
columna "aún sin desenlace registrado" y la describía como si incluyera
"tanto los casos que siguen abiertos como el residuo de condición
desconocida" — eso era impreciso. La última columna es **S(t)**, la
supervivencia general de "cualquier evento de localización": casos que
siguen literalmente `DESAPARECIDO`, sin ningún evento observado
todavía, de ningún tipo. Los casos de condición **DESCONOCIDA** NO
pertenecen a esa columna — ya tuvieron un evento (sí fueron
localizados), solo que sin condición capturada; por eso ahora tienen su
propia columna. Confundir ambas cosas hacía parecer que había más
casos "sin resolver" de los que realmente hay.

**Verificación de consistencia interna:** los cuatro componentes de
cada fila (CON VIDA + SIN VIDA + DESCONOCIDA + S(t)) suman exactamente
100%, y CON VIDA + SIN VIDA + DESCONOCIDA reproduce EXACTAMENTE el
Kaplan-Meier general de "cualquier localización" (a ≤3 días: 31.71869%
+ 2.17374% + 0.12536% = 34.01779%, idéntico al 34.02% —redondeado
34.0%— ya reportado en §2/README, verificado a 5 decimales) — a
diferencia de la versión con jitter, donde esa suma dejaba una
diferencia de ~1.4 puntos que se documentó entonces como "artefacto
numérico aceptable". Con el cálculo exacto y el corte corregido, no
queda ninguna diferencia que explicar: es una identidad matemática que
se cumple sin margen bajo los datos actuales, y esa misma identidad
(`tests/test_outcomes.py`) es la prueba de regresión que detectó el
segundo defecto (censura restada dos veces) descrito arriba en cuanto
se corrigió el corte.

Fuente: `outputs/tables/outcome_cif_summary.csv`,
`outcome_cif_curve_con_vida.csv`, `outcome_cif_curve_sin_vida.csv`.
Gráficos: `outputs/charts/07_outcome_intervals.png`,
`08_outcome_cif.png`, `09_outcome_naive_vs_correct.png`.

### Dos métricas de SIN VIDA que no deben confundirse ni intercambiarse

§13 y §14 responden preguntas distintas y usan poblaciones distintas —
mezclarlas produce lecturas erróneas del tipo "solo 3.5% termina SIN
VIDA" cuando en realidad esa cifra y el 10.8%/4.8% de §13 miden cosas
diferentes:

| Métrica | Qué mide | Población (denominador) | Ejemplo |
|---|---|---|---|
| **Proporción SIN VIDA entre localizados con condición conocida** (§13) | De los casos que YA se sabe cómo terminaron, qué fracción fue SIN VIDA | Solo localizados con `location_condition` conocida (n=1,750: 1,026 hombres + 724 mujeres); no exige fecha de localización válida, no dice nada sobre cuánto tardó el caso | Hombres: 111/1,026 = **10.8%** [IC 95% Wilson: 9.1%-12.9%] |
| **Probabilidad acumulada de desenlace SIN VIDA** (CIF, Aalen-Johansen, §14) | De TODOS los casos que entraron al análisis de tiempo —incluidos los que siguen abiertos y por tanto aún no han tenido "tiempo" de terminar en nada— qué fracción terminó SIN VIDA dentro de X días | Población completa en riesgo (n=2,394, de los cuales 1,182 siguen abiertos) | A ≤30 días desde el reporte: **3.54%** |

La segunda cifra es más baja que la primera no porque el riesgo real sea
menor, sino porque su denominador incluye a todos los casos aún sin
desenlace (que "diluyen" la proporción) y porque mide una ventana de
tiempo fija, no el desenlace final de cada caso. Ninguna de las dos es
"la cifra correcta" en abstracto — cada una responde una pregunta
distinta, y ambas deben citarse con su etiqueta completa, nunca solo
como "% SIN VIDA" a secas.

**Limitación pendiente:** las cifras de §13 sí tienen intervalo de
confianza (Wilson). Las de §14 (Aalen-Johansen) actualmente NO tienen
intervalo de confianza calculado en este proyecto — lifelines puede
calcularlo, pero no está implementado todavía. Esto no es un error de
cálculo, es una pieza no construida: cualquier cifra de §14 debe leerse
como una estimación puntual, sin margen de incertidumbre cuantificado.

## 15. Qué NO se puede afirmar con esto (además de lo ya dicho en §10)

- **`location_date` no es la fecha de fallecimiento.** No existe esa
  columna en el archivo fuente. Ningún número de §11-§14 debe leerse
  como "la persona murió en tal intervalo de tiempo desde el reporte o
  la desaparición" — solo se sabe cuándo se cerró el caso, no cuándo
  ocurrió el desenlace en sí.
- **No se puede afirmar que buscar más rápido habría evitado un
  desenlace SIN VIDA.** La asociación entre tiempo transcurrido y
  proporción de SIN VIDA (§12, §14) es consistente con varias
  explicaciones que este dato no permite distinguir: que el tiempo en
  sí incremente el riesgo, que casos con mayor riesgo desde el inicio
  (por circunstancia de la desaparición, no capturada aquí con detalle
  utilizable) tiendan también a tardar más en cerrarse, o una mezcla de
  ambas. Ninguna de las cifras aquí aísla esos mecanismos.
- **Las diferencias por sexo y edad (§13) son asociaciones, no
  explicaciones.** No se investigó aquí por qué existen.
- **La alcaldía, con esta muestra, no mostró una diferencia
  estadísticamente sostenible** en el desenlace (IC traslapados) — no
  se debe repetir en otro contexto como si fuera un hallazgo firme.

## 16. Qué haría falta para ir más allá de la asociación

Ninguno de estos datos existe en el archivo fuente actual; se listan
porque son los que se necesitarían para pasar de "está asociado" a
"esto explicaría el mecanismo":

- Circunstancias de la desaparición en forma estructurada y utilizable
  (la columna existente, `disappearance_circumstances`, es texto libre
  y no se usa cuantitativamente — ver `docs/DATA_DICTIONARY.md`).
- Estado de salud previo o factores de riesgo conocidos al momento del
  reporte (no al momento de la localización).
- Recursos de búsqueda efectivamente desplegados por caso (número de
  personas, tipo de búsqueda, si se activó protocolo Alba u otro).
- Una fecha o ventana estimada del desenlace en sí (no disponible;
  requeriría fuente distinta, p. ej. dictámenes forenses).

## 17. Acciones propuestas orientadas a prevenir desenlaces graves

Con la reserva explícita de que nada aquí es causal (§15): estas son
hipótesis de acción razonables a partir de una asociación observada, no
recomendaciones con eficacia demostrada. Se separan explícitamente en
sustentadas por el dato disponible vs. hipótesis que requieren datos que
este proyecto no tiene.

**Resumen de las tres acciones:**

| Hallazgo | Acción propuesta | Mecanismo hipotético | Información faltante | Cómo evaluar su efecto |
|---|---|---|---|---|
| El % de desenlace SIN VIDA es más bajo en intervalos cortos y más alto en los largos (5.4% en ≤1 día → 19.0% en >30 días, reloj reporte), sin ser estrictamente creciente en cada intervalo intermedio (§12, §14) | Priorizar recursos de búsqueda en la ventana temprana (72 horas) — propuesta a evaluar, eficacia no demostrada | Si el tiempo en sí incrementa el riesgo (no solo refleja que los casos graves tardan más), concentrar recursos temprano podría reducir la exposición | Circunstancias de la desaparición en forma estructurada, para separar "el tiempo causa riesgo" de "los casos graves tardan más"; también falta para evaluar costo y factibilidad operativa | Comparar la proporción SIN VIDA por intervalo (tabla de §12) en cohortes futuras con y sin el refuerzo, con un grupo de comparación real — no solo antes/después |
| No existe fecha del desenlace en sí, solo `location_date`, y no hay respaldo documental de que equivalga al cierre administrativo del expediente (§11, §15) | Que la Comisión capture una fecha o ventana estimada del desenlace, distinta de `location_date` | Sin este dato, una mejora en "tiempo hasta la fecha registrada" puede no adelantar el momento real en que se encuentra a la persona | El dato en sí — esta acción existe para producirlo | Una vez capturado, comparar la brecha entre la fecha del desenlace real y `location_date`; si es grande y variable, las cifras actuales subestiman la urgencia real |
| La brecha por sexo (10.8% hombres vs. 4.8% mujeres, IC 95% no traslapados; §13) y el gradiente por edad no tienen explicación en los datos disponibles | Revisión cualitativa de una muestra de expedientes SIN VIDA (con salvaguardas éticas) antes de diseñar cualquier intervención dirigida por sexo o edad | Ninguno propuesto todavía — es el paso previo para poder proponer uno con fundamento, no especulación | `disappearance_circumstances` en forma estructurada (hoy es texto libre) + acceso a expedientes con protecciones de privacidad | Es diagnóstico, no intervención: "funciona" si produce una hipótesis de mecanismo concreta y verificable |

**Aclaración importante sobre la Acción 1 —** el gradiente por sexo y
edad de §13 es una asociación real y sustentada por los datos. Lo que
NO está sustentado, ni aquí ni en ninguna otra fuente citada por este
proyecto, es que **priorizar recursos de búsqueda específicamente por
sexo o edad reduzca desenlaces SIN VIDA** — eso es una hipótesis sin
evaluar, no una recomendación. La Acción 1 de abajo se refiere
únicamente a la ventana de **tiempo** (72 horas), no a ningún grupo
demográfico. Nada en este proyecto debe usarse para justificar reducir
la prioridad, la urgencia o los recursos asignados a la búsqueda de
mujeres, personas jóvenes, o cualquier otro grupo: la ausencia de una
proporción de SIN VIDA más alta en esos grupos no dice nada sobre la
urgencia de un caso individual. Investigar el porqué de esa brecha,
sin actuar sobre ella todavía, es exactamente lo que propone la Acción
3.

### Acción 1 — Priorizar recursos de búsqueda en la ventana temprana tras el reporte (propuesta evaluable, con eficacia pendiente de comprobar)

- **Evidencia**: §12 y §14 muestran que, en general, la proporción de
  desenlace SIN VIDA es más baja en los intervalos cortos y más alta en
  los largos (5.4% en ≤1 día → 19.0% en >30 días, reloj reporte) —
  aunque el patrón no es estrictamente creciente en cada intervalo
  intermedio (ver la corrección en §12); la mayoría de la resolución
  rápida es CON VIDA, no SIN VIDA (§14).
- **Acción propuesta**: priorizar recursos de búsqueda en la ventana
  temprana (primeras 72 horas) en vez de repartirlos de forma pareja en
  el tiempo. Esto es una propuesta a evaluar, no una recomendación con
  eficacia demostrada — no se afirma aquí que sea de bajo costo, que ya
  sea práctica común, ni que vaya a funcionar.
- **Mecanismo hipotético**: si el paso del tiempo incrementa por sí
  mismo el riesgo (y no solo refleja que los casos más graves tardan
  más por otra razón), concentrar recursos temprano podría reducir el
  tiempo hasta la localización y, con ello, la exposición a ese riesgo.
  Es una hipótesis, no un mecanismo confirmado.
- **Datos adicionales necesarios**: para saber si el mecanismo
  hipotetizado es el correcto (y no una alternativa igualmente
  consistente con los datos): circunstancias de la desaparición en
  forma estructurada, para poder separar "el tiempo causa riesgo" de
  "los casos graves tardan más". Sin ese dato, tampoco se puede evaluar
  el costo real ni la factibilidad operativa de la propuesta — ninguna
  de las dos cosas se documenta en este proyecto.
- **Cómo evaluar si funciona**: comparar, en cohortes de reportes de
  periodos futuros con y sin el refuerzo, la proporción SIN VIDA por
  intervalo de tiempo (misma tabla de §12) antes y después del cambio
  operativo, idealmente con periodos o unidades de comparación (p. ej.
  alcaldías) que reciban el refuerzo en momentos distintos. Una simple
  comparación de "antes vs. después" sin grupo de comparación sería
  débil porque no controla por tendencia temporal general.

### Acción 2 — Registrar sistemáticamente la fecha (o ventana) del desenlace, no solo la fecha de localización capturada (hipótesis por probar, requiere dato nuevo)

- **Evidencia**: §11 y la advertencia de §15 — hoy no existe ninguna
  columna con la fecha del desenlace en sí, solo `location_date`, y el
  registro no documenta si esa fecha corresponde al momento del
  desenlace, al cierre administrativo del expediente, o a otro punto
  del proceso — esa equivalencia no está respaldada por
  `docs/DATA_DICTIONARY.md` ni por ninguna otra fuente citada aquí.
  Esto impide, con los datos actuales, distinguir cuánto del tiempo
  "reporte→localización" ocurrió antes vs. después del desenlace real.
- **Acción**: que la Comisión capture (si no lo hace ya internamente)
  una fecha o ventana estimada del desenlace en sí, distinta de
  `location_date`.
- **Mecanismo hipotético**: sin este dato, cualquier intervención sobre
  "tiempo hasta la fecha registrada" puede estar acortando un trámite o
  un proceso de captura sin necesariamente adelantar el momento real en
  que se encuentra a la persona — no se puede saber cuál de las dos
  cosas está pasando con los datos actuales.
- **Datos adicionales necesarios**: el dato en sí es lo que falta —
  esta acción existe precisamente para producirlo.
- **Cómo evaluar si funciona**: una vez capturado, comparar la brecha
  entre la fecha del desenlace real y `location_date`; si esa brecha es
  grande y variable, confirma que las cifras actuales de este proyecto
  subestiman la urgencia real; si es pequeña y estable, las cifras
  actuales son un proxy razonable.

### Acción 3 — Investigar cualitativamente la brecha por sexo (11% vs. 5%) antes de proponer una intervención específica (hipótesis por probar, requiere dato nuevo)

- **Evidencia**: §13 — la diferencia por sexo es la más clara
  estadísticamente de las tres (IC no traslapados), pero el dato
  disponible no explica el porqué.
- **Acción**: antes de diseñar cualquier intervención dirigida por
  sexo, una revisión cualitativa de una muestra de expedientes SIN VIDA
  (con las salvaguardas éticas correspondientes) para identificar si
  hay un patrón de circunstancia común (tipo de desaparición, contexto)
  que explique la brecha, en vez de asumir que el sexo por sí mismo es
  el factor relevante.
- **Mecanismo hipotético**: ninguno propuesto todavía — esta acción es,
  explícitamente, el paso previo para poder proponer uno con fundamento
  en vez de especular.
- **Datos adicionales necesarios**: `disappearance_circumstances` en
  forma estructurada (hoy es texto libre, ver §16), y acceso a
  expedientes con las protecciones de privacidad correspondientes.
- **Cómo evaluar si funciona**: esta acción en sí es de diagnóstico, no
  de intervención — "funciona" si produce una hipótesis de mecanismo
  concreta y verificable; el paso de evaluación de una intervención
  vendría después, una vez exista esa hipótesis.

**Ninguna de estas tres acciones debe presentarse como una reducción de
mortalidad demostrada, ni tiene su eficacia comprobada.** La Acción 1 es
la única cuya premisa (la asociación entre tiempo y desenlace) está
sustentada directamente por los datos de este proyecto — pero eso
sustenta la asociación, no la eficacia de la acción propuesta, que
sigue siendo una hipótesis a evaluar como cualquier otra intervención
(§17, nota sobre la Acción 1). Las Acciones 2 y 3 son explícitamente
pasos para conseguir el dato que hoy falta, no recomendaciones de
intervención en sí mismas.

---

# §18. Revisión v0.2 (2026-10-11) — cifras que sustituyen a §2, §5 y §6

Motivo y método: `docs/METHODOLOGY.md` §13. Fuente: `outputs/tables/*_v02.csv`.
**Las cifras de §2 (34.0%), §5 (sexo sin diferencia) y §6 (12-17 el grupo más lento)
quedan superadas.** §14 (Aalen-Johansen exacto) sigue vigente para su población.
Las secciones anteriores se conservan sin editar para trazabilidad.

## 18.1 Pregunta central: % con localización documentada desde el reporte

| Escenario | n | ≤1 día | ≤3 días | ≤7 días | ≤30 días |
|---|---|---|---|---|---|
| E0 (población v79, corte corregido) | 2,392 | 26.5 | 34.0 | 40.3 | 47.4 |
| E1 (+ localizados antes del registro) | 2,710 | 35.1 | 41.7 | 47.3 | 53.6 |
| E2-baja (sin fecha = no localizados) | 2,937 | 32.4 | 38.5 | 43.6 | 49.4 |
| **E3 principal** | 2,937 | **37.2** | **44.2** | **50.1** | **56.8** |
| E3 IC 95% bootstrap | | 35.3–39.0 | 42.3–46.2 | 48.2–52.1 | 54.9–58.6 |
| E2-alta (sin fecha = día 0) | 2,937 | 40.1 | 46.2 | 51.4 | 57.2 |

Lectura: aprox. **44%** de los casos recibidos tenía localización documentada a
≤3 días calendario del reporte (rango 38.5%–46.2% según cómo se traten los 227
localizados sin fecha). La cifra publicada antes (34.0%) excluía 564 localizados.
Mensaje metodológico central: la misma base produce cifras que difieren hasta
~12 puntos según decisiones de tratamiento de datos; deben declararse siempre.

## 18.2 Con vida / sin vida (Aalen-Johansen exacto)

Población de §14 (2,394): sin cambios respecto a la versión base (CON VIDA ≤3 d
31.72%, SIN VIDA ≤3 d 2.17%; ver `outcome_cif_summary.csv`).

E3 (estimación principal): CON VIDA ≤3 d **40.7%** [38.7–42.6], ≤30 d 51.8%;
SIN VIDA ≤3 d **3.1%** [2.5–3.8], ≤30 d 4.4% [3.7–5.2].
Recordatorio: la fecha de localización es la fecha registrada; NO es fecha de
fallecimiento y la fuente no documenta a qué momento del proceso corresponde (§15 sigue vigente).

## 18.3 Características (E3, % ≤3 días, IC 95%) — asociación, no causa

- **Sexo:** mujeres 48.6% [45.8–51.6] vs. hombres 41.4% [39.4–43.4]. Los IC no se
  traslapan: **sustituye la conclusión de §5** («sin diferencia»), que solo miraba
  a los ya localizados.
- **Edad:** 60+ 55.4% [50.2–60.1] (el más alto); 12-17 48.8% [44.5–52.8];
  18-29 45.3%; 0-11 39.1%; 30-44 39.8%; 45-59 39.0%. **Sustituye §6**: los
  adolescentes ya no son el grupo más lento.
- **Año de reporte:** 2019 40.4% · 2020 52.2% · 2021 47.5% · 2022 32.9%. La caída
  de 2022 puede reflejar rezago en la actualización del estatus (ver §18.4).
- **Fuente:** NOTICIA 46.4% [44.3–48.3] vs. REPORTE 38.8% [35.7–42.0].
- **Alcaldía:** IC amplios y traslapados (aprox. 43%–54% entre alcaldías con ≥30
  localizaciones). Sin alcaldía registrada: 25.6% [20.6–31.0], la más baja: la
  falta de dato se asocia con menor localización documentada. No se presenta
  ranking.

## 18.4 Limitación principal pendiente (H5)

43.7% de los reportes de 2019 y 50.8% de 2022 seguían «DESAPARECIDO» al corte.
No se puede distinguir desaparición prolongada de estatus no actualizado. Prueba
propuesta (doc 03 §7): cotejar contra una versión pública posterior del registro.
