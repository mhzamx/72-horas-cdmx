# Metodología

## 1. Unidad de análisis

Un registro público de una persona reportada como desaparecida ante la
Comisión de Búsqueda de Personas de la Ciudad de México (CBPCDMX). El
proyecto trabaja con datos disociados y publica únicamente código y
estadísticas agregadas (ver `docs/ETHICS.md`).

## 2. Dos relojes, dos preguntas distintas

| Reloj | Ancla (t=0) | Evento | Pregunta que responde |
|---|---|---|---|
| **Hechos → reporte** | `missing_date` | `report_date` | ¿Cuánto tarda una desaparición en llegar al registro? |
| **Reporte → localización** | `report_date` | `location_date` | ¿Cuánto tarda el sistema, desde que tiene el caso, en localizar a la persona? Es el reloj central de "72 HORAS". |
| **Desaparición → localización** *(alterno)* | `missing_date` | `location_date` | Igual que el anterior, pero sin excluir a quienes fueron localizados antes de que el reporte quedara registrado. |

No se mezclan entre sí. El reloj "reporte → localización" es el que
responde la pregunta central del proyecto porque mide lo que el sistema
de búsqueda controla una vez que tiene el caso; el reloj alterno
"desaparición → localización" existe porque, como se explica en la
sección 4, hay casos reales donde localización y registro no ocurren en
el orden esperado.

### Precisión temporal

La fuente solo trae fecha (día), no hora. Por eso "72 horas" se reporta
técnicamente como **≤3 días calendario observados**, no como 72 horas
exactas. Esto es una limitación de la fuente, documentada, no un ajuste
oculto.

## 3. Dos preguntas que NO son la misma (A vs. B)

Esta distinción es el corazón metodológico del proyecto:

> **(A) "De los casos que YA fueron localizados, ¿qué porcentaje se
> localizó dentro de 72 horas?"**
> Denominador: solo casos con `is_located = 1` y duración válida desde
> el reporte. Es un KPI simple, fácil de calcular y de explicar, pero
> tiene un sesgo: como los casos que tardan más en resolverse tardan
> más en *entrar* a este denominador (o simplemente siguen abiertos y
> nunca entran), este número **sobreestima** la velocidad real del
> sistema. Se calcula en `vw_kpi_overview` / `vw_borough_kpis` / etc.
> como `pct_located_le_Xd_among_located`.

> **(B) "Considerando también los casos aún no localizados, ¿qué
> proporción de TODOS los reportes ya estaba localizada a las 72
> horas?"**
> Denominador: todos los casos con `report_date` válido que entraron a
> la línea de tiempo (`valid_for_report_timeline = 1`), estén o no
> localizados. Esta pregunta se responde de dos formas complementarias:
>
> - **KPI de cohorte madura** (`vw_report_cohorts`,
>   `pct_matured_reports_located_le_3d`): para cada mes de reporte,
>   solo se calcula el % a 3 días entre los reportes que ya tienen al
>   menos 3 días de antigüedad al momento del corte del extracto (para
>   no penalizar cohortes recién llegadas que no han tenido tiempo de
>   madurar).
> - **Kaplan-Meier** (`vw_survival_input`, `outputs/tables/survival_kpis.csv`):
>   la versión estadísticamente correcta. Cada caso abierto se trata
>   como observación censurada (sabemos que a la fecha de corte seguía
>   sin localizarse, pero no cuándo se resolverá). Es el número que
>   debe citarse cuando se hable de "% localizado a 72 horas" en un
>   contexto donde importa no sobreestimar.

En los datos de este extracto, (A) da **67.1%** localizado en ≤3 días
entre los ya localizados, mientras que (B) vía Kaplan-Meier da **34.0%**
del total de casos en riesgo. La diferencia (33 puntos) no es un error:
es exactamente el efecto de que ~40% de los casos del extracto seguían
abiertos a la fecha de corte y (A) los ignora por completo. Ver
`outputs/FINAL_FINDINGS.md` para la lectura completa.

## 4. Por qué "localizado antes del reporte" NO es un error automático

`location_date < report_date` ocurre en 337 casos (11.4% del total). La
tentación es marcarlo como "dato corrupto", pero hay una explicación
legítima: la Comisión puede formalizar/capturar el reporte en el sistema
**después** de que la persona ya fue encontrada (por ejemplo, si la
localización ocurrió muy rápido, o si hay rezago administrativo en la
captura). De estos 337 casos, la clasificación real tiene tres partes,
no dos:

- **315** tienen `missing_date` conocida y `location_date >=
  missing_date` (orden perfectamente posible respecto a la
  desaparición, solo "temprano" respecto al registro del reporte).
- **3** tienen `missing_date` faltante -- no hay forma de determinar si
  el orden respecto a la desaparición es posible o imposible, así que
  no se les asume ninguno de los dos.
- Los dos grupos anteriores (315 + 3 = **318**) se clasifican como
  **AMBIGUOUS**, no como error: el primero porque el orden sí es
  posible, el segundo porque no hay evidencia para clasificarlo de
  otra forma -- "sin evidencia de que sea imposible" no es lo mismo
  que "confirmado como posible", y el texto no debe leerse como si lo
  fuera.
- Los otros **19** sí tienen `location_date < missing_date`: eso **sí**
  es lógicamente imposible (nadie puede ser localizado antes de
  desaparecer) y se clasifican como **IMPOSSIBLE**.

**Chequeo global relacionado, pero distinto** (`location_before_event`
en `src/quality.py`, ver §5): compara `location_date < missing_date`
sobre **todo** el dataset, no solo sobre estos 337, y da **21** casos.
19 de ellos son los mismos IMPOSSIBLE de arriba; los otros **2**
(case_key 390 y 2494) tienen `location_date >= report_date` -- por eso
no forman parte de los 337 de esta sección -- pero igual tienen
`location_date < missing_date` (en ambos casos, `missing_date` es
notablemente más tardía que `report_date` y que `location_date`,
consistente con el mismo tipo de anomalía de captura). No cambian la
clasificación de los 337 de arriba; se documentan aparte para que el
21 y el 19 no se confundan entre sí.

Consecuencia práctica: los 337 casos se excluyen del reloj "reporte →
localización" (porque ahí su duración sería negativa/indefinida) pero
los 318 ambiguos SÍ se incluyen en el reloj alterno "desaparición →
localización", que es precisamente para qué existe ese segundo reloj.
Ningún caso se elimina del conteo general de localizados/abiertos.

## 5. Categorías de calidad (`src/quality.py`)

| Categoría | Significado | Regla | ¿Se excluye de algún análisis? |
|---|---|---|---|
| MISSING | Falta un dato necesario | `missing_report_date`, `missing_event_date`, `missing_location_date`, `missing_borough` | Sí, del análisis que necesite ese campo específico. |
| IMPOSSIBLE | Orden de fechas lógicamente imposible | `location_before_event`, `report_before_event` | Sí, de ambos relojes de tiempo. Se documentan como posible error de captura. |
| AMBIGUOUS | Orden inusual pero explicable (sección 4) | `location_before_report` | Solo del reloj "reporte → localización"; se incluye en el reloj "desaparición → localización". |
| MISMATCH | El estatus no cuadra con las fechas capturadas | `status_located_without_location_date` (227 casos: dice LOCALIZADO pero no hay fecha de localización utilizable), `status_missing_with_location_date` (0 casos en este extracto) | El caso sigue contando como localizado en los totales generales, pero no puede tener una duración calculada. |
| DUPLICATE | Mismo contenido en todas las columnas salvo el ID | `duplicate_content` (16 filas / 7 grupos) | No se elimina ninguna fila. Se documenta para que quien reutilice los datos decida. |
| OUTLIER | Valor extremo pero plausible | `historic_missing_date` (77 casos con desaparición reportada hace más de 10 años respecto al inicio de la ventana de reportes: casos de larga data) | No se excluye de los totales; sí se excluye del cálculo de "tiempo típico" hechos→reporte (`docs` / `reporting_delay_distribution.csv`) porque distorsiona el promedio. |

Ningún flag borra una fila de `cases_raw`. Las exclusiones ocurren solo
en las vistas analíticas (`sql/02_views.sql`), de forma explícita y
documentada por columna (`valid_for_report_timeline`,
`excluded_from_report_timeline_reason`, etc.).

## 6. Umbrales de tiempo

Se reportan ≤1, ≤3, ≤7 y ≤30 días (calendario). El umbral de 72
horas/3 días es el foco comunicativo del proyecto, **no** una sugerencia
de que la búsqueda deba esperar ese plazo: el marco normativo vigente
exige búsqueda inmediata desde el primer reporte.

## 7. Análisis de supervivencia

- Evento = localización con duración válida desde el reporte
  (`is_located = 1 AND report_to_location_days IS NOT NULL`).
- Censura = caso todavía abierto (`is_located = 0`), censurado a la
  fecha de corte del extracto (`EXTRACT_CUTOFF_DATE`, ver §7.1).
- **Corrección de esta revisión.** Los casos LOCALIZADO sin duración
  reporte→localización válida (los 564 de la sección 4: 227 sin fecha
  de localización utilizable, 318 ambiguos y 19 con orden imposible)
  **NO** se tratan como censurados en el Kaplan-Meier actual — una
  versión anterior de esta página los describía así, y era impreciso.
  En realidad quedan **excluidos por completo** de `vw_survival_input`
  (`WHERE valid_for_report_timeline = 1`): no cuentan como evento, no
  cuentan como censura, no aparecen en la población de riesgo en
  ningún momento. Población real de `vw_survival_input`: **1,212**
  eventos con duración válida + **1,182** casos abiertos (censurados)
  = **2,394** casos en riesgo — no 2,958 (el total de reportes) ni
  2,958 menos solo los abiertos. (El reparto exacto 1,212/1,182, en vez
  de 1,213/1,181, es efecto de la corrección de consistencia del corte
  descrita en §7.2 — un caso más re-censurado, no un cambio en el total
  de casos en riesgo.)
- Curva general (`outputs/tables/survival_curve.csv`) y curvas por
  sexo, alcaldía y grupo de edad (`survival_by_*.csv`), estas últimas
  **solo** para grupos con al menos 30 casos en riesgo
  (`MIN_SAMPLE_SIZE` en `src/analysis.py`).
- Calculado a mano (Kaplan-Meier explícito, sin `lifelines`) para poder
  explicar cada paso en una entrevista: en cada tiempo de evento, la
  probabilidad acumulada de "seguir sin localización" se multiplica por
  `(1 - eventos / en_riesgo)`.

### 7.1 Fecha de corte del extracto (`EXTRACT_CUTOFF_DATE`)

**Qué se corrigió.** El corte administrativo (la fecha "hasta la cual"
se considera observado un caso abierto) se inferÍa antes como
`MAX(report_date, location_date)` sobre todo el dataset. Eso es frágil
por construcción: un solo registro con una fecha de evento atípica
puede desplazar un parámetro que afecta a los 1,181 casos abiertos del
proyecto. Ocurrió exactamente eso con el caso **ID 1138**: reportado el
2021-09-07, con `location_date = 2022-12-15` (más de 15 meses después),
mientras que el último reporte real en todo el archivo es del
2022-11-14 y ningún otro caso tiene `location_date` posterior al
2022-11-10. Usar el máximo de esa columna movía el corte del proyecto
un mes completo (de 2022-11-15 a 2022-12-15) sin ninguna revisión.

**El caso ID 1138 en sí.** No se declara "perfectamente legítimo" ni
"error de captura" — ninguna de las dos cosas tiene evidencia
documental en este extracto. Lo que sí se observa, de forma neutral:
sus vecinos inmediatos por ID (1133–1140, reportados en la misma
semana de septiembre de 2021) se localizaron todos en días o semanas
desde su reporte; el ID y `report_date` tienen una correlación de
-0.996 en todo el dataset (el registro asigna IDs en orden
cronológico inverso: IDs bajos = reportes recientes), consistente con
un identificador secuencial estable, no con una fecha corrupta que
además corrompería el ID. Ambas lecturas —una resolución real
excepcionalmente tardía, o un error de captura en el año de
`location_date`— siguen siendo posibles; no hay en este archivo un
campo de auditoría o metadato que permita decidir entre ellas.

**Fecha de corte elegida: 2022-11-15**, documentada como constante
explícita en `src/config.py::EXTRACT_CUTOFF_DATE` (usada también,
como literal SQL, en `vw_report_cohorts` y `vw_survival_input` de
`sql/02_views.sql`). Evidencia disponible (ver
`docs/SOURCE_ACCESS.md`): el nombre del archivo fuente,
`registro-interno-cbp-15-noviembre.xlsx`, y que el último reporte real
es 2022-11-14 (un día antes). Es evidencia interna consistente, **no**
una confirmación oficial de la fecha exacta en que se generó el
extracto — se documenta como la mejor suposición disponible.

**Análisis de sensibilidad** (2022-11-15 vs. el corte anterior,
derivado del outlier, 2022-12-15): los resultados que dependen poco de
la cola más reciente del extracto casi no cambian (KM general a ≤1/≤3
días, las dos señales de presión ya reportadas en 2019-12 y 2021-05 —
idénticas byte a byte bajo ambos cortes). Los que sí cambian de forma
visible son los que dependen directamente de qué tan "maduros" se
consideran los meses más recientes: los KPI de cohorte madura de
`vw_report_cohorts` para los reportes de 2022-10 y 2022-11 (menos
casos alcanzan el umbral de "observado ≥30 días" bajo el corte más
temprano, así que el denominador madurado de esos meses se reduce o,
en 2022-11, se queda sin ningún mes maduro a 30 días) y, en menor
medida, el propio Kaplan-Meier/CIF general a 7 y 30 días (cambios de
decenas de centésimas de punto porcentual — ver `CHANGELOG.md` para
las cifras exactas). Ningún hallazgo reportado en
`outputs/FINAL_FINDINGS.md` depende de los meses 2022-10/2022-11
como evidencia por sí sola.

### 7.2 Consistencia entre el corte y `location_date` (corrección posterior)

Fijar `EXTRACT_CUTOFF_DATE` (§7.1) no bastaba por sí solo: quedaba una
inconsistencia residual. El caso ID 1138 tiene `location_date` =
2022-12-15, **posterior** al corte de 2022-11-15 -- pero antes de esta
corrección, tanto `vw_survival_input` como el modelo de riesgos
competitivos (`src/outcomes.py`) seguían tratándolo como un evento CON
VIDA observado a los 464 días (`report_to_location_days`), sin
comparar esa fecha contra el corte. Es inconsistente con la propia
definición del corte: si el extracto se congeló el 2022-11-15, un
desenlace fechado después no podía conocerse todavía en ese momento.

**Corrección:** tanto `vw_survival_input`
(`date(location_date) <= date(max_date)`) como
`export_outcome_competing_risk` en `src/outcomes.py` (misma
comparación, en Python, porque ahí el corte es la constante
`EXTRACT_CUTOFF_DATE` y no conviene duplicarla como un tercer literal
SQL) ahora re-censuran al corte cualquier caso cuyo `location_date` sea
posterior a él: pasa a contar como abierto, con duración = corte −
reporte, en vez de como evento observado más allá de la ventana de
observación. Verificado: **ID 1138 es el único caso del extracto** con
esta condición.

**Efecto en las cifras.** Población de `vw_survival_input`: **1,212**
eventos con duración válida + **1,182** casos abiertos (antes: 1,213 +
1,181) = 2,394 sin cambio. Los umbrales reportados (≤1/≤3/≤7/≤30 días,
tanto en el Kaplan-Meier general como en el CIF de riesgos
competitivos) **no cambian**: la duración de este caso, re-censurada
(~434 días) o como evento (464 días), excede los 30 días bajo
cualquiera de las dos interpretaciones, así que nunca entra en esos
umbrales. Sí cambia la cola de la curva completa de riesgos
competitivos (`outcome_cif_curve_con_vida.csv`, día ≥434): la CIF final
de CON VIDA baja de 47.11% a 47.04% (un evento CON VIDA menos en el
total). Ningún hallazgo de `outputs/FINAL_FINDINGS.md` cita esa cola de
la curva ni el valor final de la CIF -- todos los hallazgos reportados
usan los umbrales ≤1/≤3/≤7/≤30 días, que quedan intactos.

## 8. Comparaciones entre grupos (alcaldía, sexo, edad, año)

Reglas fijas para todas las comparaciones:

1. Se reporta siempre el tamaño de muestra (`sample_size`) junto al
   indicador.
2. Grupos con menos de 30 casos se conservan en los CSV (transparencia)
   pero se excluyen de gráficos comparativos (`below_min_sample_size`).
3. Ninguna diferencia entre grupos se interpreta como causal: pueden
   reflejar composición de casos, calidad de captura local, u otros
   factores no observados en este registro.
4. No se presentan diferencias de pocos puntos porcentuales entre
   grupos de tamaño similar como "hallazgos": se contextualizan como
   variación dentro de lo esperable salvo que la magnitud y el N
   sugieran lo contrario.

## 9. Presión operativa

Señal descriptiva (no causal, no un modelo predictivo) que se activa
cuando coinciden, en el mismo mes:

1. Volumen de reportes con z-score ≥ 2 respecto a su media móvil de 12
   meses, y
2. Deterioro del % de localización en ≤3 días (cohortes maduras) frente
   a su propia media móvil de 6 meses.

Es una señal para priorizar revisión operativa, no una acusación ni un
diagnóstico de causa.

## 10. Flujo vs. resolución vs. stock

Tres cosas distintas que el proyecto reporta por separado:

- **Flujo de entrada**: reportes nuevos por mes (`vw_monthly_flow.reports`).
- **Resolución**: localizaciones por mes (`vw_monthly_flow.localizations`),
  que no corresponden necesariamente a reportes del mismo mes.
- **Stock de casos abiertos**: backlog acumulado, aproximado por el
  `net_backlog_flow` mensual (reportes − localizaciones) y, de forma más
  rigurosa, por la curva de Kaplan-Meier (población "en riesgo" en cada
  punto del tiempo).

## 11. Reproducibilidad

El archivo fuente permanece intacto en `data/raw/`. Todo lo demás —
base SQLite, tablas, gráficos, tablas para Power BI — se regenera desde
cero con `python -m src.run_all`. Ver `README.md`.

## 12. Ampliación: desenlaces CON VIDA / SIN VIDA

Esta sección documenta la metodología de `src/outcomes.py` (pasos
11-13 de `src/run_all.py`). No modifica nada de las secciones 1-11.

**Qué es `location_condition`.** Columna original `Condicion.localizacion`
del archivo fuente, mapeada desde el inicio del proyecto
(`docs/DATA_DICTIONARY.md`) pero no usada analíticamente hasta ahora.
Solo existe para casos con estatus LOCALIZADO — verificado exhaustivamente
contra el archivo crudo: 0 casos con estatus DESAPARECIDO tienen esta
columna no nula. De los 1,777 localizados: 1,612 CON VIDA, 147 SIN VIDA,
18 con condición desconocida (9 de esos 18 sí tienen fecha de
localización pero no condición capturada; los otros 9 no tienen ninguna
de las dos).

**Advertencia que gobierna toda esta sección — repetida a propósito
varias veces porque es fácil de olvidar leyendo una sola cifra:**
`location_date` es la fecha que el registro captura como fecha de
localización. **No es la fecha de fallecimiento**, y el registro
tampoco documenta si equivale al cierre administrativo del expediente o
a otro momento del proceso — esa equivalencia no tiene respaldo en
`docs/DATA_DICTIONARY.md` y no se afirma aquí. Todo lo que sigue mide
asociación entre el tiempo hasta esa fecha registrada y el desenlace
capturado junto con ella — nunca cuándo ocurrió la muerte, nunca si una
búsqueda más rápida la habría evitado. Esas dos afirmaciones están
explícitamente fuera del alcance de este análisis y no deben inferirse
de ningún número aquí.

**Por qué no se reutiliza el Kaplan-Meier general (§8 de este documento,
o `vw_survival_input`).** Ese modelo trata "estar localizado" como un
único evento. Con dos desenlaces posibles (CON VIDA, SIN VIDA) que
compiten por el mismo caso, usar un Kaplan-Meier simple para SIN VIDA
—tratando CON VIDA y los casos abiertos como si fueran censura— es un
error clásico de riesgos competitivos: sobreestima la incidencia de SIN
VIDA porque ignora que el desenlace CON VIDA "retira" población en
riesgo por una razón distinta a la censura. El estimador correcto es la
función de incidencia acumulada de Aalen-Johansen.

**Corrección de esta revisión.** La primera versión de `src/outcomes.py`
calculaba esto con `lifelines.AalenJohansenFitter`, que resuelve
tiempos empatados con un jitter aleatorio continuo. Con días enteros y
empates masivos (cientos de casos localizados el mismo día), ese jitter
desplazaba una fracción real de casos a un lado u otro de umbrales
enteros como "≤1 día" — un sesgo medible, no ruido de redondeo:
verificado, CON VIDA a ≤1 día daba 20.6% con jitter vs. 25.0% con el
cálculo exacto. Se reemplazó por `_competing_risk_cif`, la fórmula
estándar de Kalbfleisch & Prentice (1980), que agrega los empates en
vez de resolverlos con aleatoriedad: determinista, sin semilla. En su
momento se verificó contra un cálculo independiente hecho sobre los
datos crudos, bajo el corte administrativo vigente entonces
(2022-12-15): a ≤3 días, CON VIDA 31.70426% y SIN VIDA 2.17210%,
coincidencia a 5 decimales.

**Corrección adicional de esta revisión.** La auditoría de la fecha de
corte (§7.1) encontró un segundo defecto, independiente del jitter, en
esta misma función: la fórmula de supervivencia restaba del riesgo
tanto los eventos reales como las salidas por censura en el mismo
paso, quitándole peso dos veces al efecto de la censura. Era
matemáticamente detectable con un ejemplo mínimo (duraciones
`[1,1,2,3]`, eventos `[evento, censurado-empatado-en-1, evento,
censurado]`: la versión con el error da 0.5 en el día 2, la correcta da
0.625 — idéntico a `lifelines.KaplanMeierFitter` sobre el mismo
ejemplo), pero era invisible con el corte anterior porque ningún caso
censurado tenía una duración corta que empatara con un evento real en
los primeros días. Al corregir el corte a 2022-11-15, sí aparecen esos
empates y el error se volvió detectable (una prueba de identidad
existente, `test_competing_risk_cif_sum_matches_any_event_km_on_real_data`,
empezó a fallar). Se corrigió quitando la censura de esa resta; se
añadió `test_cif_handles_censoring_tied_with_an_event_on_the_same_day`
como prueba de regresión. Con el corte y la fórmula ya corregidos, los
valores anteriores (31.70426%/2.17210%, verificados contra la
referencia externa bajo el corte viejo) ya no aplican tal cual —
cambiaron ligeramente porque la población de riesgo cambió, no porque
el método vuelva a estar en duda: la identidad "suma de CIF = KM de
cualquier evento" se sigue cumpliendo exactamente
(`tests/test_outcomes.py`, 25/25 pruebas), que es la verificación
disponible sobre los datos actuales. `tests/test_outcomes.py` también
incluye casos sintéticos con empates exactamente en los días 1, 3, 7 y
30 para verificar que el umbral es inclusivo del día exacto.

`src/outcomes.py` calcula **ambos** métodos — el ingenuo (mal usado) y
el correcto — para dejar documentada la magnitud real del sesgo, no
para usar el ingenuo en ningún hallazgo. Cifras vigentes tras ambas
correcciones (`outputs/tables/outcome_cif_summary.csv`):

| Día | Desenlace | Ingenuo (mal) | Correcto (exacto) | Sobreestimación relativa |
|---|---|---|---|---|
| ≤1 | CON VIDA | 25.13% | 25.02% | +0.43% |
| ≤3 | CON VIDA | 31.97% | 31.72% | +0.79% |
| ≤7 | CON VIDA | 37.91% | 37.46% | +1.20% |
| ≤30 | CON VIDA | 44.43% | 43.68% | +1.72% |
| ≤1 | SIN VIDA | 1.50% | 1.42% | +5.49% |
| ≤3 | SIN VIDA | 2.53% | 2.17% | +16.52% |
| ≤7 | SIN VIDA | 3.31% | 2.68% | +23.45% |
| ≤30 | SIN VIDA | 4.77% | 3.54% | +34.85% |

El método ingenuo sobreestima en todos los umbrales — nunca lo
subestima (ver prueba
`test_competing_risk_naive_always_overestimates_correct_method` en
`tests/test_outcomes.py`) — pero el sesgo NO es parejo entre
desenlaces: para CON VIDA (mayoritario) es pequeño (<2 puntos); para
SIN VIDA (minoritario) crece con el horizonte de tiempo hasta ser
considerable a 30 días. No se debe generalizar "el método ingenuo
distorsiona todo por igual".

**Clasificación de estado usada en el modelo de riesgos competitivos**
(`vw_outcome_competing_risk_input`), sobre la misma población que el
Kaplan-Meier general (`valid_for_report_timeline = 1`, es decir:
abiertos + localizados con duración reporte→localización limpia):

| Estado | event_type | Significa |
|---|---|---|
| Abierto | 0 (censurado) | Sigue como DESAPARECIDO al corte del extracto |
| Localizado CON VIDA | 1 | `location_condition = 'CON VIDA'` |
| Localizado SIN VIDA | 2 | `location_condition = 'SIN VIDA'` |
| Localizado, condición desconocida | 3 | Tiene duración válida pero no se capturó la condición (6 casos) |

Los 6 casos de condición desconocida se tratan como un tercer desenlace
que compite, no se reasignan a CON VIDA ni a SIN VIDA — hacerlo
inventaría un dato que no existe.

**Denominador para las comparaciones por sexo/edad/alcaldía** (ver
`outputs/FINAL_FINDINGS.md`). Ahí se usa un denominador distinto y más
amplio que el del modelo de riesgos competitivos: localizados con
`location_condition` conocida (CON VIDA o SIN VIDA), sin exigir además
duración válida. Se eligió así porque la pregunta de esa tabla es "de
los que sabemos su desenlace, ¿varía por grupo?", no "¿cuándo ocurre en
el tiempo?" — para esa segunda pregunta sí se exige duración válida
(la tabla de intervalos documenta ambos denominadores por separado). El
umbral N≥30 se aplica sobre este n analítico, con el mismo criterio ya
corregido para el análisis general de velocidad (ver `CHANGELOG.md`).

## 13. v0.2 — Correcciones de población, corte y riesgos competitivos (2026-10-11)

Especificación completa: documento «03 — METODOLOGÍA DE EJECUCIÓN v0.2 — 72 HORAS»
(Google Drive, carpeta del proyecto). Código: `src/estimands.py`. Nada de §1-§12
se borra; esta sección indica qué queda superado.

**Problema que corrige la v0.2.** La versión base ya documenta que los 564
localizados sin duración válida quedan FUERA de `vw_survival_input` (ni evento ni
censura), pero mantiene esa exclusión, mientras conserva los 1,181 abiertos.
Excluir eventos y conservar censurados sesga hacia abajo el % localizado.

**C1 — Corte fijo:** ya corregido en la versión base `entrega_validacion_final_3`
(`EXTRACT_CUTOFF_DATE = 2022-11-15`; el caso ID 1138 se re-censura). La v0.2 lo
reutiliza (`CUTOFF_DATE`) y lista ese caso en `post_cutoff_cases_v02.csv`.

**C2 — Clases de población** (fuente única `excluded_from_report_timeline_reason`):
VALIDO 1,211 · AMBIGUO 318 (localizado antes del registro del reporte) ·
SIN_FECHA 227 · IMPOSIBLE 21 (excluido de todo) · ABIERTO 1,181.
Escenarios: E0 (VALIDO+ABIERTO) · E1 (+AMBIGUO como evento en día 0) ·
E2-baja / E2-alta (+SIN_FECHA como nunca localizado / localizado en día 0) ·
**E3, estimación principal**: SIN_FECHA con imputación múltiple (M=200, seed 42)
desde la distribución observada de localizados con fecha (supuesto MAR, por eso
E2 se publica siempre como rango). IC 95%: bootstrap de casos (B=1,000, M=20).

**C3 — Aalen-Johansen exacto:** ya corregido en la versión base
(`_competing_risk_cif`, sin jitter). La v0.2 aplica el mismo estimador exacto a
las poblaciones E0-E3; control: CIF total = 1 − S_KM.

**Grupos (S3).** % ≤3 días con E3 por grupo (pool global de imputación), IC
bootstrap (B=1,000, M=10); umbral: ≥30 localizaciones observadas en el grupo.
