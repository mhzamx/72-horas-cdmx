# Changelog


## [v0.2 final — tablero para publicación] — 2026-10-15

### Corregido
- Tabla de intervalos (página 3 del tablero): ahora usa solo la clase VALIDO (1,211 casos);
  la tabla v0.1 (1,213) contaba 2 localizados con fecha anterior a la desaparición.
  Nueva salida `outputs/tables/outcome_intervals_v02.csv` (`export_outcome_intervals_v02`) y prueba.
- Textos del tablero: la fecha de localización es la registrada (no fecha de fallecimiento;
  la fuente no documenta a qué momento del proceso corresponde); versión anterior "dejaba fuera
  545 localizados que E3 sí incluye"; nota sobre los 318 localizados antes del registro (día 0);
  IC de las 13 alcaldías mostradas; denominadores de grupos con «sin dato» oculto;
  nota de 1,408 sin fecha de localización = 1,181 abiertos + 227 localizados sin fecha;
  ≤3 días calendario como aproximación operativa de 72 horas.
- Modelo de Power BI sin tablas ni medidas sin uso.

### Agregado
- `powerbi/72HORAS_v02_final.pbix` y `powerbi/72HORAS_v02_final.pdf` (5 páginas, con
  segmentadores de escenario y días en la página 2).
- Verificación independiente: reconstrucción completa desde el archivo fuente (tablas idénticas)
  y recálculo con implementación propia (lifelines) de clases, escenarios E0-E3, CIF y grupos.

### Datos excluidos del repositorio
- Archivo fuente, base SQLite y tablas a nivel de caso (`fact_cases*.csv`, muestras de casos).

## [v0.2 — Power BI validado] — 2026-10-13

Abierto en Power BI Desktop en la computadora de Miguel, actualizado y revisado
página por página. Tarjetas: 2,958 casos · 44.2% ≤3 días (E3) · 1,181 abiertos
al corte · 4.4% localizados sin vida ≤30 días.

### Corregido (diseño)
- Línea de incertidumbre recortada → una línea de ancho completo:
  «Estimación principal ≤3 días (E3): 44.2% · IC 95% 42.3–46.2% · Rango 38.5–46.2%».
- Etiqueta truncada en la tarjeta principal; barra de desplazamiento en títulos.
- Eje Y de las curvas KM y CIF arranca en 0%.
- Tablas de las páginas 2 y 5 cortadas en el PDF → fuente compacta, todas las filas visibles.

### Agregado
- `powerbi/72HORAS_v02.pbix` (producto final) y `powerbi/72HORAS_v02.pdf` (5 páginas).
- Nota: en el .pbix las tablas usan espaciado de fila 0 y fuente 8.5 (ajuste hecho en
  Power BI); `build_pbip_72h.py` genera el equivalente con fuente 8/9.

## [v0.2 — Población completa E0-E3, imputación de localizados sin fecha y análisis por grupos] — 2026-10-11

Ejecutado según «03 — METODOLOGÍA DE EJECUCIÓN v0.2 — 72 HORAS».
**Versión base: `entrega_validacion_final_3.zip`** (la más reciente, 6-sep-2026
17:19; encontrada el 11-oct en Descargas de Miguel, no estaba en Drive). Corte
fijo y Aalen-Johansen exacto ya venían corregidos en esa base. `data/raw/` sin
cambios (SHA-256 `acace3f7…a9619`). Tablas de la base regeneradas idénticas.

### Corregido
- Exclusión de 564 localizados en la estimación principal: población completa por
  clases (VALIDO 1,211 · AMBIGUO 318 · SIN_FECHA 227 · IMPOSIBLE 21 · ABIERTO
  1,181) y escenarios E0-E3; E3 principal con imputación múltiple (M=200,
  seed 42) e IC bootstrap (B=1,000).

### Agregado
- `src/estimands.py`, `src/powerbi_export_v02.py`, `src/charts_v02.py`; pasos
  14-16 en `src/run_all.py`; `tests/test_estimands.py` (6 pruebas; total 31).
- Tablas `*_v02`, gráficas 10-12, carpeta `dashboard/data_v02/`.
- `docs/METHODOLOGY.md` §13, `outputs/FINAL_FINDINGS.md` §18, pregunta rectora
  v0.2 en README (aprobada por Miguel el 11-oct-2026, «si continuemos»).

### Resultado
- % con localización documentada ≤3 días: **44.2%** [42.3–46.2] (antes 34.0%).
- Cambian sexo (§5) y edad (§6): ver FINAL_FINDINGS §18.

### Verificado
- 31/31 pruebas; pipeline de 16 pasos; cifras dentro de la tolerancia del Anexo B.

### Pendiente
- Textos de comunicación CONGELADOS (cifras superadas).
- Power BI: no existe .pbix en ninguna versión; construir con `dashboard/data_v02/`.
- Prueba de validez de «abierto» contra versión pública posterior (doc 03 §7).

## [Corrección final: consistencia corte/location_date, conteo exacto de location_before_report, y columna DESCONOCIDA en §14] — 2026-09-06

Tres correcciones puntuales de auditoría fina, no una revisión general.
`data/raw/` no se modifica (hash verificado sin cambios); no se agregó
ningún análisis nuevo. 25/25 pruebas pasan; pipeline completo
regenerado.

### 1. Un `location_date` posterior al corte seguía contando como evento observado

Fijar `EXTRACT_CUTOFF_DATE = 2022-11-15` (ronda anterior) no bastaba
por sí solo: quedaba una inconsistencia. El caso **ID 1138**
(`location_date` = 2022-12-15, posterior al corte) seguía tratándose,
tanto en `vw_survival_input` como en el modelo de riesgos
competitivos, como un evento CON VIDA observado a los 464 días — sin
comparar esa fecha contra el corte. Es contradictorio con la propia
definición del corte: un desenlace fechado después del corte no podía
conocerse "al momento del corte".

**Corrección:** `vw_survival_input` (`sql/02_views.sql`) ahora exige
`date(location_date) <= date(max_date)` para contar un caso como
evento; en caso contrario, se re-censura a la fecha de corte (cuenta
como abierto, duración = corte − reporte). `vw_outcome_competing_risk_input`
expone ahora `location_date` para que `src/outcomes.py` aplique la
misma regla en Python (el corte es una constante de `src/config.py`,
no un tercer literal SQL que sincronizar). Verificado: **ID 1138 es el
único caso del extracto** con esta condición.

**Efecto en las cifras:** ninguno en los umbrales ≤1/≤3/≤7/≤30 días
(reportados en `outputs/FINAL_FINDINGS.md`) — la duración de este caso
excede los 30 días tanto re-censurada (~434 días) como evento (464
días). Sí cambian: la población de `vw_survival_input` (1,212 eventos +
1,182 abiertos = 2,394, antes 1,213 + 1,181); `outcome_cif_summary.csv`
(n_con_vida 1,107→1,106, n_censurado_abierto 1,181→1,182, más una
columna nueva `n_recensurado_por_corte` con valor 1 para trazabilidad);
la cola de `outcome_cif_curve_con_vida.csv` desde el día 434 en
adelante, incluido el valor final de la curva (CIF CON VIDA:
47.11%→47.04%); y, en consecuencia, cambios pequeños y acotados al
mismo caso en `survival_curve.csv`, `survival_by_sex.csv`,
`survival_by_age_group.csv` y `survival_by_borough_missing.csv` (21
filas cambiadas en `survival_curve.csv`, todas desde el día 464 en
adelante). `survival_kpis.csv` no cambia en ninguno de sus 4 umbrales.

### 2. Conteo impreciso de `location_before_report` (316/21 → 315/3/19)

La documentación (no el código: la clasificación analítica 318
AMBIGUOUS + 19 IMPOSSIBLE ya era y sigue siendo correcta) describía los
337 casos con `location_date < report_date` como "316 con
`location_date >= missing_date` + 21 con orden imposible". Es
impreciso: verificado directamente sobre los datos, el desglose real
es **315** con `missing_date` conocida y orden válido, **3** con
`missing_date` faltante (sin forma de determinar el orden -- se
agrupan con los anteriores, sin asumir que el orden sea válido, dando
315+3=**318** AMBIGUOUS), y **19** con orden lógicamente imposible
(IMPOSSIBLE). Además, el chequeo global `location_before_event` (que
compara `location_date < missing_date` sobre *todo* el dataset, no
solo sobre estos 337) da **21** casos: 19 coinciden con los IMPOSSIBLE
de arriba, y los otros **2** (case_key 390 y 2494) no forman parte de
los 337 (tienen `location_date >= report_date`) pero sí tienen
`location_date < missing_date`.

**Corrección:** texto actualizado en `outputs/FINAL_FINDINGS.md` (§1 y
§3), `docs/METHODOLOGY.md` (§4) y `docs/interview_notes.md`. Ninguna
cifra de ninguna tabla CSV cambia -- es una corrección de prosa, no de
cálculo.

### 3. §14 de FINAL_FINDINGS.md: la última columna es S(t), no "abiertos + desconocida"

La tabla de resultados del modelo de riesgos competitivos tenía una
columna "% aún sin desenlace registrado" descrita como si incluyera
"tanto los casos que siguen abiertos como el residuo de condición
desconocida". Es impreciso: esa columna es **S(t)**, la supervivencia
general de "cualquier evento de localización" -- casos que siguen
`DESAPARECIDO`, sin ningún evento de ningún tipo. Los casos
DESCONOCIDA ya tuvieron un evento (sí fueron localizados, solo que sin
condición capturada) y no pertenecen a esa columna.

**Corrección:** `src/outcomes.py::export_outcome_competing_risk` ahora
también exporta el CIF de DESCONOCIDA (`event_type=3`), que ya se
calculaba internamente (para que la identidad de suma cerrara) pero no
se exponía -- nuevo archivo `outcome_cif_curve_desconocida.csv` y
nuevas filas `DESCONOCIDA` en `outcome_cif_summary.csv` (sin
comparación "ingenuo vs. correcto": no aplica, no es un hallazgo del
proyecto). La tabla de `outputs/FINAL_FINDINGS.md` §14 ahora tiene
cuatro columnas (CON VIDA, SIN VIDA, DESCONOCIDA, S(t)) que suman
exactamente 100%, con la descripción de S(t) corregida. Ningún valor
numérico de las columnas CON VIDA/SIN VIDA cambia por esta corrección
en sí (los valores de DESCONOCIDA y S(t) ya estaban calculados
correctamente antes, solo mal etiquetados/agrupados en el texto);
`tests/test_outcomes.py::test_competing_risk_naive_always_overestimates_correct_method`
se ajustó para comparar solo CON VIDA/SIN VIDA contra el método
ingenuo (DESCONOCIDA no tiene un ingenuo comparable por diseño).

### Verificación final

25/25 pruebas (`pytest -q`), pipeline completo (`python -m src.run_all`,
13/13 pasos), hash SHA-256 de `data/raw/` sin cambios antes y después.

## [Corrección: fecha de corte administrativa, segundo defecto en el CIF, y descripción de censura en METHODOLOGY.md] — 2026-09-06

Última ronda de correcciones antes de congelar el proyecto. `data/raw/`
no se modifica (hash SHA-256 verificado sin cambios antes y después);
ningún análisis nuevo se agregó. Tres hallazgos independientes, los dos
primeros conectados: auditar la fecha de corte expuso un segundo bug
de cálculo que llevaba dormido desde la revisión anterior.

### 1. Fecha de corte administrativa frágil (`MAX(report_date, location_date)`)

**El problema.** El corte usado para censurar los casos abiertos en
`vw_survival_input` y `vw_report_cohorts` se inferÍa como el máximo de
`report_date`/`location_date` sobre todo el dataset. Es un método
frágil: un solo registro con una fecha de evento atípica puede mover
un parámetro que afecta a los 1,181 casos abiertos del proyecto. Ocurrió
exactamente eso con el caso **ID 1138** (reportado 2021-09-07,
`location_date` = 2022-12-15 — más de 15 meses después, y posterior a
*cualquier otra* fecha de localización del archivo; la siguiente más
tardía es 2022-11-10). Ese único valor desplazaba el corte real del
proyecto de 2022-11-15 a 2022-12-15 sin ninguna revisión.

El caso ID 1138 en sí **no se declara** legítimo ni erróneo: sus
vecinos inmediatos por ID (1133-1140, misma semana de reporte) se
localizan todos en días/semanas, no meses, lo cual es sugerente pero no
concluyente; el ID y `report_date` tienen correlación -0.996 en todo
el archivo (secuencia cronológica inversa), lo cual no distingue entre
un desenlace real tardío y un año mal capturado. No hay evidencia
documental para decidir entre las dos lecturas — se documenta la
anomalía sin forzar una conclusión (ver `docs/SOURCE_ACCESS.md`).

**Corrección.** Se reemplazó el cálculo automático por una constante
explícita y documentada, `EXTRACT_CUTOFF_DATE = "2022-11-15"` en
`src/config.py`, propagada como literal a `sql/02_views.sql`
(`vw_report_cohorts`, `vw_survival_input` — sin templating, se
mantiene sincronizada a mano) y usada en `src/outcomes.py`. Evidencia
para ese valor: el nombre del archivo fuente
(`registro-interno-cbp-15-noviembre.xlsx`) y que el último reporte real
es 2022-11-14, un día antes — evidencia interna consistente, no una
confirmación oficial. Se documenta la incertidumbre residual y se hizo
un análisis de sensibilidad (ver más abajo y `docs/SOURCE_ACCESS.md`)
en vez de tratar el valor como un hecho verificado.

### 2. Segundo defecto en `_competing_risk_cif`: censura restada dos veces

Al corregir el corte, una prueba que siempre había pasado
(`test_competing_risk_cif_sum_matches_any_event_km_on_real_data`)
empezó a fallar: la suma de las CIF de todos los desenlaces dejó de
igualar exactamente el Kaplan-Meier de "cualquier evento". La causa:
la fórmula de supervivencia de `_competing_risk_cif` restaba del riesgo
tanto los eventos reales como las salidas por censura en el mismo
paso — doble conteo del efecto de la censura, cuando esta ya se
refleja correctamente al reducir el denominador (`n_en_riesgo`) del
paso siguiente, porque los censurados dejan de cumplir
`duration >= t`.

Demostrado con un ejemplo mínimo: duraciones `[1,1,2,3]`, eventos
`[evento, censurado (empatado en el día 1), evento, censurado]` — la
fórmula con el error da 0.5 acumulado al día 2; la fórmula corregida
da 0.625, idéntico a `lifelines.KaplanMeierFitter` sobre el mismo
ejemplo. El bug existía desde la revisión anterior (cuando se
implementó `_competing_risk_cif`) pero era matemáticamente inerte bajo
el corte viejo (2022-12-15): ningún caso censurado tenía entonces una
duración corta que empatara con un evento real en los primeros días.
Al corregir el corte, aparecieron esos empates y el error se volvió
detectable — exactamente el patrón de "una corrección no relacionada
expone un error dormido" que este proceso de auditoría ya había
detectado antes.

**Corrección:** se quitó la censura de la resta de supervivencia en
`_competing_risk_cif` (`src/outcomes.py`). Se añadió
`test_cif_handles_censoring_tied_with_an_event_on_the_same_day` en
`tests/test_outcomes.py` como prueba de regresión permanente. Total de
pruebas: 24 → **25**, todas pasan.

**Consecuencia honesta:** los valores 31.70426%/2.17210% (≤3 días,
CON VIDA/SIN VIDA) verificados en la revisión anterior contra una
referencia externa fueron calculados bajo el corte viejo y con la
fórmula con el bug. Ya no describen la población actual — cambiaron a
31.71869%/2.17374%, una diferencia pequeña pero real, producto de
ambas correcciones combinadas. La verificación disponible sobre los
datos ya corregidos no es esa referencia externa puntual, sino la
identidad matemática interna (suma de CIF = KM de cualquier evento),
que se sigue cumpliendo exactamente.

### 3. `docs/METHODOLOGY.md`: censurado vs. excluido

El texto anterior describía los casos LOCALIZADO sin duración
reporte→localización válida como "censurados" en el Kaplan-Meier. Es
impreciso: esos 564 casos (227 sin fecha de localización utilizable,
318 ambiguos, 19 con orden imposible) están **excluidos por completo**
de `vw_survival_input` (`WHERE valid_for_report_timeline = 1`) — no
cuentan como evento ni como censura, no aparecen en la población de
riesgo en ningún momento. Población real de `vw_survival_input`:
**1,213** eventos con duración válida + **1,181** casos abiertos
(censurados) = **2,394** casos en riesgo. Corregido en
`docs/METHODOLOGY.md` §7.

### Cifras que cambiaron (regeneradas con `python -m src.run_all`;
### ver diffs completos en el propio repositorio)

Archivos con cambios numéricos reales (10 de las tablas en
`outputs/tables/`), todos por la combinación de ambas correcciones de
esta ronda:

- **`survival_kpis.csv`** (KM general, cita en §1-2 de
  `outputs/FINAL_FINDINGS.md`): ≤1d sin cambio (26.48%); ≤3d 34.00% →
  **34.02%** (sigue redondeando a 34.0%); ≤7d 40.27% → **40.35%**
  (redondea a 40.4%, antes 40.3%); ≤30d 47.16% → **47.43%** (redondea a
  47.4%, antes 47.2%).
- **`outcome_cif_summary.csv`** (§14): ≤1d sin cambio (CON VIDA
  25.02%, SIN VIDA 1.42%); ≤3d CON VIDA 31.70%→**31.72%**, SIN VIDA
  2.17%→**2.17%** (cambio bajo el redondeo a 2 decimales, real a más
  decimales: 2.17210%→2.17374%); ≤7d CON VIDA 37.39%→**37.46%**, SIN
  VIDA 2.67%→**2.68%**; ≤30d CON VIDA 43.44%→**43.68%**, SIN VIDA
  3.51%→**3.54%**.
- **`outcome_cif_curve_con_vida.csv`, `outcome_cif_curve_sin_vida.csv`,
  `survival_curve.csv`, `survival_by_sex.csv`,
  `survival_by_age_group.csv`, `survival_by_borough_missing.csv`**:
  cambios pequeños y pervasivos en cada paso de cada curva (esperado:
  la población en riesgo de `vw_survival_input` cambió en cada punto
  del tiempo al mover el corte un mes). Ningún hallazgo cualitativo de
  §11-§13 de `outputs/FINAL_FINDINGS.md` (comparaciones por sexo, edad,
  alcaldía) cambia de signo o de conclusión.
- **`cohort_resolution.csv`**: `avg_observed_days` de cada mes baja 30
  días (efecto directo y esperado del corte). Cambio con consecuencia
  real: los denominadores "maduros" a 30 días de los meses **2022-10**
  (82→43 reportes maduros, tasa 46.34%→48.84%) y **2022-11** (49→0
  reportes maduros a 30 días; a 3 días 49→42, a 7 días 49→25) se
  reducen, porque bajo el corte corregido esos meses son más recientes
  respecto al corte. Ningún hallazgo de `outputs/FINAL_FINDINGS.md`
  citaba esos dos meses como evidencia aislada.
- **`pressure_signals.csv`**: solo 2 filas no relacionadas con señales
  cambian (2022-11, 2022-12 — meses fuera de ventana o con muestra
  mínima). Las dos señales de presión ya reportadas (**2019-12**,
  **2021-05**) son byte-idénticas antes y después — no dependen del
  corte.

Sin cambios: `data/raw/` (hash verificado), `outcome_by_sex.csv`,
`outcome_by_age_group.csv`, `outcome_by_borough.csv`, `quality_flags.csv`
y el resto de tablas que no dependen de `vw_survival_input` /
`vw_report_cohorts` / `vw_outcome_competing_risk_input`.

### Archivos de documentación actualizados

`docs/METHODOLOGY.md` (§7 censurado-vs-excluido, nueva §7.1 sobre el
corte, tabla de §14 con cifras nuevas), `docs/SOURCE_ACCESS.md` (nueva
sección de auditoría del corte, caso 1138, sensibilidad), `src/config.py`
(constante `EXTRACT_CUTOFF_DATE` documentada), `sql/02_views.sql`
(literal del corte en 2 vistas), `src/outcomes.py` (fórmula corregida),
`tests/test_outcomes.py` (nueva prueba de regresión), `README.md`
(conteo de pruebas), `outputs/FINAL_FINDINGS.md` (§2 y §14 con cifras
nuevas y explicación de ambas correcciones).

## [Corrección: jitter en Aalen-Johansen, generalizaciones y afirmaciones sin respaldo] — 2026-09-06

Corrección sustantiva de cálculo -- no solo de texto. Encontrada por
verificación externa independiente (referencia recibida: a ≤3 días
desde crudo, CON VIDA 31.70426%, SIN VIDA 2.17210%). `data/raw/` no se
modifica; los resultados de §1-§10 (velocidad de localización, KM
general, señales de presión) no cambian.

### Bug de fondo: jitter de `lifelines.AalenJohansenFitter`

`src/outcomes.py` calculaba la incidencia acumulada (CIF) de
CON VIDA/SIN VIDA con `AalenJohansenFitter`, que resuelve tiempos
empatados con un jitter aleatorio continuo (advertencia explícita de la
librería). Con datos en días enteros y empates masivos (cientos de
casos localizados el mismo día 0 o día 1), ese jitter desplazaba una
fracción real de esos casos a un lado u otro de un umbral entero como
"≤1 día" -- no es ruido de redondeo, es un sesgo medible: a ≤1 día, CON
VIDA daba 20.55% con jitter vs. **25.02% con el cálculo exacto**, una
diferencia de ~4.5 puntos causada enteramente por el jitter.

**Corrección:** se implementó `_competing_risk_cif` en
`src/outcomes.py`, el estimador estándar de incidencia acumulada
(Kalbfleisch & Prentice 1980) que agrega los empates en lugar de
romperlos con aleatoriedad -- determinista, sin semilla. Se retiró
`lifelines.AalenJohansenFitter` de este cálculo (la constante `_AJ_SEED`
queda documentada como histórica en el módulo, sin uso). El cálculo del
método ingenuo (Kaplan-Meier estándar de un solo evento) no cambia: ese
maneja empates correctamente de forma nativa, sin jitter.

**Verificación:**
- Contra la referencia externa: a ≤3 días, este proyecto ahora produce
  CON VIDA 31.70426% y SIN VIDA 2.17210% -- coincide con la referencia
  recibida a 5 decimales.
- Identidad matemática (antes no se cumplía exactamente, ahora sí a 5
  decimales): la suma de los CIF de los tres tipos de evento (CON VIDA
  + SIN VIDA + DESCONOCIDA) en cualquier día debe igualar el
  Kaplan-Meier de "cualquier evento" sobre la misma población. A ≤3
  días: 31.70426% + 2.17210% + 0.12531% = 34.00167%, idéntico al 34.0%
  ya establecido en §2/README del proyecto. Con el jitter, esa suma
  dejaba una diferencia de ~1.4 puntos que se había documentado
  incorrectamente como "artefacto numérico aceptable" -- no lo era, era
  el síntoma del bug.
- Nuevas pruebas en `tests/test_outcomes.py`: `_competing_risk_cif`
  probado con un caso sintético de 10 personas con empates exactamente
  en los días 1, 3, 7 y 30, con valores esperados calculados a mano;
  prueba explícita de que el umbral es inclusivo del día exacto (un
  evento en el día 3 cuenta dentro de "≤3 días"); prueba de la
  identidad CIF-suma-igual-a-KM-general tanto en datos sintéticos como
  en los datos reales del proyecto. Total de pruebas: 20 → 24, todas
  pasan.

### Cifras que cambian (todas en §14 de `outputs/FINAL_FINDINGS.md` y
### §12 de `docs/METHODOLOGY.md`)

| Umbral | Desenlace | Antes (con jitter) | Ahora (exacto) |
|---|---|---|---|
| ≤1 día | CON VIDA | 20.6% | 25.02% |
| ≤3 días | CON VIDA | 30.4% | 31.70% |
| ≤7 días | CON VIDA | 36.8% | 37.39% |
| ≤30 días | CON VIDA | 43.4% | 43.44% |
| ≤1 día | SIN VIDA | 1.25% | 1.42% |
| ≤3 días | SIN VIDA | 2.05% | 2.17% |
| ≤7 días | SIN VIDA | 2.59% | 2.67% |
| ≤30 días | SIN VIDA | 3.51% | 3.51% |

La sobreestimación del método ingenuo también se recalculó: antes se
describía como "sistemática y creciente" usando solo SIN VIDA (+20.0%
a +34.5%); con el cálculo correcto, CON VIDA apenas se sobreestima
(+0.4% a +1.7%) mientras que SIN VIDA sí muestra una sobreestimación
creciente y considerable (+5.5% a +34.5%) -- el sesgo es real pero
mucho más pronunciado en el desenlace minoritario que en el
mayoritario, no uniforme como se afirmó antes.

### Generalizaciones corregidas (sin cambio de cálculo, solo de texto)

- **§12 (intervalos de tiempo):** se retiró la afirmación "el patrón es
  el mismo bajo ambos relojes... crece conforme crece el tiempo, nunca
  al revés". Es cierta para el reloj desaparición→localización
  (estrictamente creciente en los 5 intervalos), pero FALSA para el
  reloj reporte→localización, que cae de 10.0% (>1-3 días) a 8.0%
  (>3-7 días) antes de volver a subir. Corregido para describir ambos
  patrones con precisión.
- **§13 (edad):** se retiró "gradiente claro" -- 60+ (11.3%) no es más
  alto que 45-59 (12.5%), no hay crecimiento continuo con la edad
  dentro de la población adulta. Se verificaron programáticamente los
  15 pares de intervalos de confianza posibles: 12-17 no se traslapa
  con NINGÚN grupo adulto (18-29, 30-44, 45-59, 60+), pero 0-11 sí se
  traslapa con 18-29 (contrario a lo que se afirmaba antes, que agrupaba
  "0-11 y 12-17" como igualmente separados de "los adultos").
- **§13 (alcaldía):** se verificaron programáticamente los 91 pares de
  intervalos de confianza posibles entre las 14 alcaldías con N≥30 --
  cero pares disjuntos, confirmando (no solo por los extremos, sino
  exhaustivamente) que el traslape es total.
- **§11, §14, §17 (Acción 2), METHODOLOGY.md §12:** se retiró la
  afirmación de que `location_date` "es la fecha en que el caso se
  cerró administrativamente" -- esa equivalencia no tiene respaldo en
  `docs/DATA_DICTIONARY.md`. Se reformuló como "la fecha que el
  registro captura como fecha de localización", sin asumir que
  corresponde a un cierre administrativo formal.
- **§17 (Acción 1):** se retiró "es de bajo costo y ya es práctica
  común en búsqueda de personas" -- afirmación sin ninguna fuente
  citada en el proyecto. La acción queda como propuesta evaluable, con
  costo, factibilidad y eficacia explícitamente pendientes de
  comprobar, no como recomendación de bajo riesgo.
- **`docs/executive_summary.md`:** actualizado el rango de alcaldías
  ("55% a 79%" → "61.5% a 78.9%", cifra ya correcta en
  `outputs/FINAL_FINDINGS.md` desde la corrección anterior pero no
  propagada aquí) y el número de señales de presión operativa ("3
  meses puntuales" → "2 meses puntuales", consistente con la corrección
  de contaminación del baseline ya aplicada a `pressure_signals`).

### Verificado tras esta corrección

- 24/24 pruebas pasan (`pytest -q`), sin advertencias de jitter.
- Pipeline completo (`python -m src.run_all`) corre sin errores.
- Hash de `data/raw/registro-interno-cbp-15-noviembre.xlsx` sin cambios
  (`acace3f70109a79181389f3af4c41f44a73e6b33661b7fc423a6b170aa3d9619`).
- `kpi_overview.csv` (67.11%), `pressure_signals.csv` (únicas señales:
  2019-12 z=2.73, 2021-05 z=3.36) y el resto de §1-§10 verificados sin
  cambios.

## [Aclaración: interpretación de acciones y métricas de desenlace] — 2026-09-06

Cambio de documentación únicamente. No modifica `data/raw/`, no modifica
ningún cálculo, script, vista SQL ni resultado numérico existente.
`src/`, `sql/`, `tests/` quedan sin tocar en esta entrada.

- **§17 (`outputs/FINAL_FINDINGS.md`):** se corrige una imprecisión
  introducida en una respuesta de chat (no en el documento) que
  describió la Acción 1 como "priorizar recursos por sexo y edad".
  Eso nunca estuvo en el documento — la Acción 1 siempre fue sobre la
  ventana de tiempo (72 horas). Se añade una aclaración explícita: la
  asociación por sexo/edad (§13) está sustentada; la eficacia de
  redirigir recursos por sexo o edad NO lo está; y ninguna cifra de
  este proyecto debe usarse para reducir prioridad o urgencia a algún
  grupo. Se añade también una tabla resumen de las tres acciones
  (hallazgo → acción → mecanismo hipotético → información faltante →
  cómo evaluar).
- **§14 (`outputs/FINAL_FINDINGS.md`):** se añade una nota explícita
  distinguiendo dos métricas de "SIN VIDA" que no deben confundirse:
  la proporción entre localizados con condición conocida (§13, con IC
  Wilson) y la probabilidad acumulada de Aalen-Johansen (§14, sin IC
  calculado todavía — limitación declarada, no corregida en esta
  entrada porque no es un error, es una pieza no construida).
- **Verificado tras el cambio:** 20/20 pruebas pasan; pipeline completo
  ejecutado sin errores; hash de `data/raw/` sin cambios
  (`acace3f70109a79181389f3af4c41f44a73e6b33661b7fc423a6b170aa3d9619`);
  todas las cifras de §1-§16 comparadas y sin cambios respecto a la
  entrada anterior.

## [Ampliación: desenlaces CON VIDA / SIN VIDA] — 2026-09-06

Ampliación del proyecto, no una corrección. No modifica ningún archivo
ni resultado de las secciones 1-10 de `outputs/FINAL_FINDINGS.md` ni de
`outputs/tables/` existentes — todo lo nuevo vive en archivos y
funciones adicionales.

### Agregado

- `src/outcomes.py` (nuevo módulo, separado de `analysis.py`): audita
  `location_condition` (columna original `Condicion.localizacion`, ya
  mapeada desde el inicio del proyecto pero nunca usada
  analíticamente), calcula desenlace por intervalo de tiempo en los dos
  relojes, desenlace por sexo/edad/alcaldía con intervalo de confianza
  de Wilson, y un modelo de riesgos competitivos (Aalen-Johansen) para
  CON VIDA / SIN VIDA — con comparación explícita contra el método
  ingenuo (Kaplan-Meier simple mal usado) para dejar medido el sesgo de
  usar el método incorrecto (sobreestimación de +20% a +34.5% según el
  umbral de días).
- `sql/02_views.sql`: 7 vistas nuevas (`vw_outcome_overview`,
  `vw_outcome_sex_kpis`, `vw_outcome_age_group_kpis`,
  `vw_outcome_borough_kpis`, `vw_outcome_interval_report`,
  `vw_outcome_interval_missing`, `vw_outcome_competing_risk_input`),
  agregadas al final del archivo sin tocar ninguna vista existente.
- `src/charts.py`: 3 gráficos nuevos (`07_outcome_intervals.png`,
  `08_outcome_cif.png`, `09_outcome_naive_vs_correct.png`) vía
  `make_outcome_charts()`, función nueva que no toca `make_charts()`.
- `src/run_all.py`: 3 pasos nuevos (11-13), pipeline ahora de 13 pasos
  en vez de 10. Los pasos 1-10 no cambiaron de lógica, solo se
  renumeró el contador impreso en pantalla (`[n/13]` en vez de
  `[n/10]`).
- `tests/test_outcomes.py` (nuevo archivo, 9 pruebas): valores conocidos
  de `wilson_ci`, reconciliación de conteos del punto 1, invariantes de
  denominador del punto 2, cotas válidas de intervalo de confianza del
  punto 3, y la prueba metodológica central —
  `test_competing_risk_naive_always_overestimates_correct_method` —
  que falla si el método ingenuo dejara de sobreestimar al correcto.
  Total de pruebas: de 11 a 20.
- `docs/METHODOLOGY.md` §12: metodología completa de riesgos
  competitivos, con la tabla ingenuo-vs-correcto y la advertencia de
  que `location_date` no es fecha de fallecimiento.
- `outputs/FINAL_FINDINGS.md` §11-§17: auditoría de `location_condition`,
  desenlace por intervalo de tiempo (dos relojes), diferencias por
  sexo/edad/alcaldía con IC de Wilson, resultado del modelo de riesgos
  competitivos, límites explícitos (§15: no se afirma fecha de
  fallecimiento ni que buscar más rápido hubiera evitado un desenlace),
  qué datos harían falta para ir más allá de la asociación (§16), y
  hasta 3 acciones preventivas propuestas con evidencia/mecanismo/datos
  necesarios/forma de evaluar, separando lo sustentado de lo hipotético
  (§17).

### Corregido durante la construcción de esta ampliación (autodetectado, no reportado por el usuario)

- `AalenJohansenFitter` resuelve empates de tiempo con un jitter
  aleatorio; sin pasar `seed=` al **constructor** (pasar
  `np.random.seed()` por fuera no basta, porque internamente la
  librería llama `np.random.seed(self._seed)` con `self._seed=None`,
  lo que resiembra desde el reloj del sistema), el pipeline daba un CIF
  ligeramente distinto en cada corrida. Verificado con `seed=42` en el
  constructor: tres corridas consecutivas del pipeline dan exactamente
  el mismo `outcome_cif_summary.csv`.
- `wilson_ci(0, n)` podía devolver un límite inferior negativo
  minúsculo (ej. `-1.2e-17`) por precisión de punto flotante en vez de
  exactamente 0. Se agregó un `clamp` a `[0, 1]` en la función.
- Un párrafo de `outputs/FINAL_FINDINGS.md` §11 citaba 189 casos
  "localizados con condición conocida pero sin fecha utilizable"; la
  cifra correcta, verificada contra `vw_cases` (que ya normaliza el
  placeholder `"/  /"` a fecha nula) en vez del archivo Excel crudo sin
  procesar, es 218. Corregido antes de publicar, junto con una
  referencia cruzada a §8 que debía decir §9 tras la renumeración de la
  corrección anterior.

### Verificado

- `pytest -q` (vía `python -m pytest -q`): 20/20 pasan.
- Pipeline completo (`python -m src.run_all`, 13 pasos): sin errores.
- `data/raw/registro-interno-cbp-15-noviembre.xlsx` sin modificar
  (hash SHA-256 idéntico antes y después:
  `acace3f70109a79181389f3af4c41f44a73e6b33661b7fc423a6b170aa3d9619`).
- Ningún valor de `outputs/tables/*.csv` de las secciones 1-10
  (borough_kpis, sex_kpis, age_group_kpis, pressure_signals,
  kpi_overview, etc.) cambió tras esta ampliación.

### No se hizo (fuera de alcance de esta ampliación)

- No se investigó la razón de la brecha por sexo (§17, Acción 3) —
  requiere datos que el proyecto no tiene (circunstancia de la
  desaparición en forma estructurada).
- No se afirma en ningún lugar que exista una reducción de mortalidad
  demostrada, ni se declara el proyecto terminado — quedan hipótesis
  explícitas sin dato para probarlas (§16, §17).

## [Corrección: umbral sobre n analítico y contaminación del z-score] — 2026-09-06

Segunda pasada de corrección, sobre los dos puntos pendientes que había
dejado la revisión anterior (mismo día). Alcance limitado a lo pedido.

### Corregido

- `src/analysis.py::_flag_small_samples`: el umbral mínimo de 30 casos
  para comparar alcaldía/sexo/edad/año ahora se aplica sobre
  `located_with_valid_duration` (n analítico, el denominador real del
  KPI), no sobre `sample_size` (N total del grupo). Efecto real:
  Cuajimalpa de Morelos (n analítico=23) y La Magdalena Contreras (n
  analítico=20) ya no entran en la comparación de alcaldías — antes
  pasaban el filtro por tener N total ≥30 aunque su porcentaje se
  calculaba sobre menos de 30 casos. El rango de `outputs/tables/borough_kpis.csv`
  se mantiene igual (nadie cambió de porcentaje); solo cambió
  `below_min_sample_size` para esas dos alcaldías, y con ello el rango
  citado en `outputs/FINAL_FINDINGS.md` §4 (antes 55.0%–78.9%, ahora
  61.5%–78.9%). Sexo, edad y año no cambian (todos sus grupos ya
  tenían n analítico ≥30).
- `src/analysis.py::export_pressure_signals`: la media/desviación móvil
  de 12 meses usada para el z-score de volumen de reportes arrastraba
  los 5 meses de relleno anteriores a la ventana real de reportes (ver
  entrada anterior sobre "48 meses") como si fueran meses reales con 0
  reportes, inflando el z-score de los primeros meses de la ventana.
  Se enmascararon esos meses (NaN en vez de 0) antes de calcular la
  línea base, para que `min_periods` exija meses reales de historia.
  Efecto real: **2019-11 deja de ser una señal de presión** (con solo
  5 meses reales de historia previa, no alcanza el mínimo de 6 que el
  método siempre exigió — su z-score pasa a ser indeterminado, no
  cero). 2019-12 se mantiene como señal con z corregido de 2.73 (antes
  3.46, contaminado). 2021-05 no cambia. `outputs/FINAL_FINDINGS.md`
  §7 actualizado de "3 meses" a "2 meses" (2019-12 y 2021-05).

### Verificado (sin alterar ningún otro resultado)

- `pytest -q` (vía `python -m pytest -q`): 11/11 pasan.
- Pipeline completo (`python -m src.run_all`) ejecutado sin errores.
- El `report_z` cambia de valor en los meses de transición 2019-07 a
  2020-05 (la línea base de 12 meses todavía incluye, por posición,
  algún mes de relleno hasta que este rota fuera de la ventana móvil),
  pero se verificó explícitamente, mes por mes, que en **ninguno** de
  esos meses cambia el resultado final `pressure_signal` — excepto
  2019-11, que pasa de 1 a 0 porque, además, deja de tener línea base
  suficiente (mínimo de 6 meses reales). De 2020-06 en adelante los
  z-scores son idénticos a los de la versión anterior (la ventana móvil
  de 12 meses ya no roza los meses de relleno). Se confirmó también que
  sexo, edad y año no tienen ningún grupo con n analítico por debajo de
  30 que el cambio de umbral debiera excluir.

## [Corrección: doble N y verificación de "48 meses"] — 2026-09-06

Corrección puntual solicitada tras revisión de `outputs/FINAL_FINDINGS.md`.
Alcance limitado a lo pedido: no se tocó ningún valor numérico ya
calculado; solo se agregó transparencia y una columna nueva.

### Corregido

- `outputs/FINAL_FINDINGS.md` §4 (alcaldía), §5 (sexo) y §6 (edad):
  cada porcentaje ahora muestra explícitamente **N total** del grupo
  (`sample_size`) y **n analítico** (`located_with_valid_duration`,
  el denominador real del KPI), que no son el mismo número. Antes el
  texto citaba solo `sample_size` junto al porcentaje, dando la
  impresión de que ese era el tamaño de muestra del cálculo.

### Verificado (sin alterar resultados)

- Los "48 meses" de `pressure_signals.csv` / `monthly_flow.csv` son
  correctos, no un bug: `vw_monthly_flow` construye su eje de meses
  como la unión de meses con reporte y meses con localización, y 6
  meses solo tienen localización (5 antes de la ventana de reportes,
  1 después). 42 meses de reportes + 6 = 48. Se agregó la columna
  `in_report_window` a ambos CSV (vía `src/analysis.py`) para hacer
  esta distinción explícita sin tocar ninguna cifra existente.
- Al desglosar por las dos N, se detectó una inconsistencia real (no
  corregida en esta pasada, documentada en §4 de `FINAL_FINDINGS.md`
  como decisión pendiente): el umbral N≥30 que filtra qué alcaldías
  se comparan se aplica sobre N total, no sobre n analítico. Dos
  alcaldías (Cuajimalpa de Morelos, La Magdalena Contreras) pasan el
  filtro de N total pero su n analítico real es menor a 30. No se
  cambió el umbral porque hacerlo alteraría qué alcaldías aparecen en
  el rango citado, y el pedido explícito era no alterar resultados
  hasta verificar.
- `pytest -q` (vía `python -m pytest -q`): 11/11 pasan. Pipeline
  completo (`python -m src.run_all`) ejecutado sin errores; todos los
  valores previamente reportados en `outputs/tables/*.csv` se
  confirmaron sin cambios salvo la columna nueva `in_report_window`.

## [Auditoría y refactor completo] — 2026-09-06

Auditoría integral del proyecto (código, SQL, calidad de datos,
documentación) con la base real `registro-interno-cbp-15-noviembre.xlsx`
ya disponible en `data/raw/`. `data/raw/` no fue modificado en ningún
momento.

### Corregido

- **Sesgo metodológico central**: `valid_for_time_analysis` excluía por
  igual casos con orden de fechas imposible y casos con
  `location_date < report_date` (317+ casos legítimos donde la persona
  fue localizada antes de que el reporte quedara registrado). Se
  separaron en categorías `IMPOSSIBLE` vs. `AMBIGUOUS`
  (`src/quality.py`, `sql/02_views.sql`) y se agregó un segundo reloj
  de tiempo ("desde la desaparición") para no perder esos casos.
- `age_group` recomendado en `data/source_contract.json` nunca se
  generaba: `Edad` es numérica en la fuente, no venía agrupada.
  Se agregó derivación explícita (`src/ingest.py::AGE_BINS`).
- Placeholders de captura (`S/D`, `S/D/` con typo, `SE DESCONOCE`,
  literal `"/  /"` en fechas) no se normalizaban a nulo: contaminaban
  agrupamientos por alcaldía/nacionalidad como si fueran categorías
  reales. Se agregó `_normalize_placeholder_series`.
- No existía un flag para el caso "estatus LOCALIZADO sin fecha de
  localización utilizable" (227 casos, 7.7% del total): se agregó
  `status_located_without_location_date`.
- `analysis.py` referenciaba `total_reports` después de que la vista se
  renombró a `sample_size`; corregido junto con la vista.
- Comparaciones por alcaldía/sexo/edad/año no aplicaban ningún umbral
  de tamaño de muestra: se agregó `MIN_SAMPLE_SIZE = 30` y
  `below_min_sample_size` en cada tabla de agregados, y se excluyen
  del gráfico (no del CSV) los grupos por debajo del umbral.
- Curva de Kaplan-Meier: la versión anterior calculaba supervivencia
  "desde el reporte" con casos que ya estaban excluidos de
  `valid_for_time_analysis`, subestimando el N en riesgo. Se
  reconstruyó sobre `vw_survival_input`, con `n_at_risk_total`
  explícito en `survival_kpis.csv`.

### Agregado

- Vistas SQL nuevas: `vw_sex_kpis`, `vw_age_group_kpis`,
  `vw_year_kpis`, `vw_survival_input`.
- `src/analysis.py`: `export_survival_by_group` (curvas por sexo,
  alcaldía y grupo de edad, con umbral de N),
  `export_reporting_delay_distribution` (impacto de outliers
  históricos en el promedio hechos→reporte), `export_quality_detail`.
- `src/powerbi_export.py`: esquema en estrella
  (`fact_cases`, `dim_date`, `dim_borough`) en `dashboard/data/`.
- 3 gráficos nuevos: evolución mensual del % localizado en ≤3 días por
  cohorte madura, distribución de tiempos (histograma), calidad de
  datos por categoría.
- `tests/test_import_logic.py`: de 1 a 11 pruebas (normalización,
  mapeo de columnas, placeholders, age_group, cada categoría de flag de
  calidad, smoke test end-to-end).
- `sql/03_analysis_queries.sql`: reescrito con 10 consultas que
  demuestran CTE, `RANK`/`DENSE_RANK`, `LAG`, promedio móvil con marco
  explícito (`ROWS BETWEEN`), `ROW_NUMBER` para top-N por grupo, y
  `HAVING` con umbral de muestra.
- Documentación nueva: `docs/DATA_DICTIONARY.md` (reescrito con EDA
  real de las 21 columnas), `docs/METHODOLOGY.md` (reescrito,
  distinción explícita entre las preguntas A y B), `outputs/FINAL_FINDINGS.md`,
  `docs/executive_summary.md`, `docs/interview_notes.md`,
  `docs/linkedin_post.md`, `docs/cv_bullets.md`,
  `dashboard/POWER_BI_GUIDE.md`.
- Documentación actualizada: `docs/SOURCE_ACCESS.md` y
  `docs/RESEARCH_LOG.md` (se documenta que el archivo real cubre
  2019-06-25 a 2022-11-14, un vintage distinto al de la página oficial
  actual y al del estudio de PLOS ONE), `README.md` (reescrito con
  resultados reales), `dashboard/POWER_BI_MODEL.md` y
  `DAX_MEASURES.md` (alineados al nuevo esquema en estrella).

### Verificado

- Pipeline ejecutado de extremo a extremo desde un estado limpio
  (sin `data/processed/`, `outputs/`, `dashboard/data/`) sin errores.
- Suite de pruebas: 11/11 pasan.
- Las 10 consultas de `sql/03_analysis_queries.sql` se ejecutaron
  manualmente contra la base generada.
- Números de `outputs/FINAL_FINDINGS.md` verificados contra los CSV de
  `outputs/tables/` generados en la corrida más reciente.

### No se hizo (fuera de alcance de esta sesión)

- No se generó el archivo `.pbix` de Power BI (requiere la aplicación
  de escritorio; se dejaron las tablas y la guía listas para
  construirlo).
- No se validó visualmente el dashboard de Power BI ya construido
  (no existe todavía como archivo).
- No se investigó cualitativamente el hallazgo de menor resolución
  rápida en el grupo de edad 12-17 años (queda como pregunta abierta
  en `outputs/FINAL_FINDINGS.md`).
