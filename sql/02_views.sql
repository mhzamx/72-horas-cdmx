-- 72 HORAS: vistas analíticas.
--
-- Capa "analytical": aquí se decide, de forma explícita y documentada,
-- qué casos entran en cada análisis. Ninguna vista borra filas de
-- cases_raw; solo las clasifica.
--
-- Dos orígenes de tiempo, porque son preguntas distintas (ver
-- docs/METHODOLOGY.md):
--   - report_to_location_days: tiempo desde que el caso se REPORTÓ a la
--     Comisión hasta la localización. Es el que responde la pregunta
--     central del proyecto ("72 horas después del reporte").
--   - missing_to_location_days: tiempo desde que la persona DESAPARECIÓ
--     hasta la localización. Incluye correctamente los casos localizados
--     antes de que el reporte quedara registrado (ver
--     excluded_from_report_timeline_reason).

DROP VIEW IF EXISTS vw_cases;
CREATE VIEW vw_cases AS
SELECT
    c.*,

    q.location_before_report,
    q.location_before_event,
    q.report_before_event,
    q.status_located_without_location_date,
    q.status_missing_with_location_date,
    q.duplicate_content,
    q.historic_missing_date,
    q.any_impossible_or_missing_core,

    -- ¿Está la persona localizada? Basado en el texto de estatus tal como
    -- lo captura la CBPCDMX (LOCALIZADO / DESAPARECIDO en este extracto).
    CASE
        WHEN UPPER(COALESCE(c.status, '')) = 'LOCALIZADO' THEN 1
        WHEN UPPER(COALESCE(c.status, '')) LIKE '%LOCALIZ%'
             AND UPPER(COALESCE(c.status, '')) NOT LIKE '%NO LOCALIZ%'
        THEN 1
        ELSE 0
    END AS is_located,

    -- Tiempo entre desaparición y reporte (requiere orden correcto).
    CASE
        WHEN c.report_date IS NOT NULL
         AND c.missing_date IS NOT NULL
         AND c.report_date >= c.missing_date
        THEN julianday(c.report_date) - julianday(c.missing_date)
    END AS event_to_report_days,

    -- Tiempo desde el REPORTE hasta la localización. NULL si el caso está
    -- abierto, si falta la fecha, o si el orden es ambiguo/imposible
    -- (ver excluded_from_report_timeline_reason para saber cuál).
    CASE
        WHEN c.location_date IS NOT NULL
         AND c.report_date IS NOT NULL
         AND c.location_date >= c.report_date
        THEN julianday(c.location_date) - julianday(c.report_date)
    END AS report_to_location_days,

    -- Tiempo desde la DESAPARICIÓN hasta la localización.
    CASE
        WHEN c.location_date IS NOT NULL
         AND c.missing_date IS NOT NULL
         AND c.location_date >= c.missing_date
        THEN julianday(c.location_date) - julianday(c.missing_date)
    END AS missing_to_location_days,

    -- ¿Este caso puede colocarse en la línea de tiempo "desde el reporte"?
    -- 1 = sí: o está abierto (aporta tiempo censurado) o está localizado
    -- con una duración limpia (localización >= reporte).
    CASE
        WHEN c.report_date IS NULL THEN 0
        WHEN UPPER(COALESCE(c.status, '')) <> 'LOCALIZADO' THEN 1
        WHEN c.location_date IS NOT NULL AND c.location_date >= c.report_date THEN 1
        ELSE 0
    END AS valid_for_report_timeline,

    -- Motivo por el que un caso LOCALIZADO queda fuera de la línea de
    -- tiempo "desde el reporte". NULL = está incluido.
    CASE
        WHEN c.report_date IS NULL THEN 'missing_report_date'
        WHEN UPPER(COALESCE(c.status, '')) <> 'LOCALIZADO' THEN NULL
        WHEN c.location_date IS NULL THEN 'status_located_without_date'
        WHEN c.location_date < c.missing_date THEN 'impossible_order'
        WHEN c.location_date < c.report_date THEN 'ambiguous_pre_registration'
        ELSE NULL
    END AS excluded_from_report_timeline_reason,

    -- Línea de tiempo "desde la desaparición": igual idea, pero el
    -- ancla es missing_date. Aquí SÍ entran los casos localizados antes
    -- del reporte (mientras la localización no sea anterior a la propia
    -- desaparición, que sería imposible).
    CASE
        WHEN c.missing_date IS NULL THEN 0
        WHEN UPPER(COALESCE(c.status, '')) <> 'LOCALIZADO' THEN 1
        WHEN c.location_date IS NOT NULL AND c.location_date >= c.missing_date THEN 1
        ELSE 0
    END AS valid_for_missing_timeline

FROM cases_raw c
JOIN quality_flags q USING(case_key);


-- ---------------------------------------------------------------------
-- KPI generales. Todos los porcentajes de tiempo se calculan SOLO sobre
-- casos localizados con duración válida desde el reporte
-- (valid_for_report_timeline = 1 AND is_located = 1): esto responde la
-- pregunta (A) "de los casos ya localizados, ¿qué tan rápido fue?".
-- La pregunta (B) "de TODOS los reportes, ¿cuántos ya estaban resueltos
-- a los N días?" se responde en vw_report_cohorts, que sí incluye a los
-- casos aún abiertos en el denominador.
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS vw_kpi_overview;
CREATE VIEW vw_kpi_overview AS
WITH located_valid AS (
    SELECT *
    FROM vw_cases
    WHERE is_located = 1 AND valid_for_report_timeline = 1
)
SELECT
    (SELECT COUNT(*) FROM vw_cases) AS total_records,
    (SELECT SUM(is_located) FROM vw_cases) AS located_records_by_status,
    (SELECT COUNT(*) - SUM(is_located) FROM vw_cases) AS open_records,
    (SELECT COUNT(*) FROM located_valid) AS located_with_valid_report_duration,
    (SELECT COUNT(*) FROM vw_cases
        WHERE is_located = 1 AND valid_for_report_timeline = 0) AS located_excluded_from_report_timeline,

    ROUND(100.0 * (SELECT SUM(CASE WHEN report_to_location_days BETWEEN 0 AND 1 THEN 1 ELSE 0 END) FROM located_valid)
        / NULLIF((SELECT COUNT(*) FROM located_valid), 0), 2) AS pct_located_le_1d_among_located,
    ROUND(100.0 * (SELECT SUM(CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END) FROM located_valid)
        / NULLIF((SELECT COUNT(*) FROM located_valid), 0), 2) AS pct_located_le_3d_among_located,
    ROUND(100.0 * (SELECT SUM(CASE WHEN report_to_location_days BETWEEN 0 AND 7 THEN 1 ELSE 0 END) FROM located_valid)
        / NULLIF((SELECT COUNT(*) FROM located_valid), 0), 2) AS pct_located_le_7d_among_located,
    ROUND(100.0 * (SELECT SUM(CASE WHEN report_to_location_days BETWEEN 0 AND 30 THEN 1 ELSE 0 END) FROM located_valid)
        / NULLIF((SELECT COUNT(*) FROM located_valid), 0), 2) AS pct_located_le_30d_among_located,

    ROUND((SELECT AVG(event_to_report_days) FROM vw_cases), 2) AS avg_event_to_report_days,
    ROUND((SELECT AVG(report_to_location_days) FROM located_valid), 2) AS avg_report_to_location_days_among_located;


-- ---------------------------------------------------------------------
-- Por alcaldía (de la desaparición). sample_size permite al consumidor
-- (Python, Power BI) decidir su propio umbral mínimo de N antes de
-- comparar; ver docs/METHODOLOGY.md, regla de "no rankings con N chico".
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS vw_borough_kpis;
CREATE VIEW vw_borough_kpis AS
SELECT
    borough_missing,
    COUNT(*) AS sample_size,
    SUM(is_located) AS located_records,
    COUNT(*) - SUM(is_located) AS open_records,
    SUM(CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END) AS located_with_valid_duration,
    ROUND(100.0 * SUM(
        CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(
        CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END
    ), 0), 2) AS pct_located_le_3d_among_located,
    ROUND(AVG(report_to_location_days), 2) AS avg_report_to_location_days
FROM vw_cases
WHERE borough_missing IS NOT NULL
GROUP BY borough_missing;


-- Por sexo.
DROP VIEW IF EXISTS vw_sex_kpis;
CREATE VIEW vw_sex_kpis AS
SELECT
    sex,
    COUNT(*) AS sample_size,
    SUM(is_located) AS located_records,
    SUM(CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END) AS located_with_valid_duration,
    ROUND(100.0 * SUM(
        CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(
        CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END
    ), 0), 2) AS pct_located_le_3d_among_located
FROM vw_cases
WHERE sex IS NOT NULL
GROUP BY sex;


-- Por grupo de edad (derivado; ver docs/data_dictionary.md).
DROP VIEW IF EXISTS vw_age_group_kpis;
CREATE VIEW vw_age_group_kpis AS
SELECT
    age_group,
    COUNT(*) AS sample_size,
    SUM(is_located) AS located_records,
    SUM(CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END) AS located_with_valid_duration,
    ROUND(100.0 * SUM(
        CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(
        CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END
    ), 0), 2) AS pct_located_le_3d_among_located
FROM vw_cases
WHERE age_group IS NOT NULL
GROUP BY age_group;


-- Por año de reporte (cohorte anual simple).
DROP VIEW IF EXISTS vw_year_kpis;
CREATE VIEW vw_year_kpis AS
SELECT
    CAST(strftime('%Y', report_date) AS INTEGER) AS report_year,
    COUNT(*) AS sample_size,
    SUM(is_located) AS located_records,
    SUM(CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END) AS located_with_valid_duration,
    ROUND(100.0 * SUM(
        CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(
        CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END
    ), 0), 2) AS pct_located_le_3d_among_located
FROM vw_cases
WHERE report_date IS NOT NULL
GROUP BY report_year;


-- ---------------------------------------------------------------------
-- Flujo mensual: entradas (reportes) vs. resoluciones (localizaciones)
-- vs. backlog neto. Esto es "flujo", no "stock" — ver vw_report_cohorts
-- para el stock de casos abiertos por cohorte.
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS vw_monthly_flow;
CREATE VIEW vw_monthly_flow AS
WITH months AS (
    SELECT substr(report_date, 1, 7) AS month
    FROM vw_cases
    WHERE report_date IS NOT NULL
    UNION
    SELECT substr(location_date, 1, 7) AS month
    FROM vw_cases
    WHERE location_date IS NOT NULL
),
reports AS (
    SELECT
        substr(report_date, 1, 7) AS month,
        COUNT(*) AS reports,
        ROUND(100.0 * SUM(
            CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
        ) / NULLIF(COUNT(*), 0), 2) AS pct_all_reports_located_le_3d
    FROM vw_cases
    WHERE report_date IS NOT NULL
    GROUP BY substr(report_date, 1, 7)
),
locs AS (
    SELECT
        substr(location_date, 1, 7) AS month,
        COUNT(*) AS localizations
    FROM vw_cases
    WHERE location_date IS NOT NULL
    GROUP BY substr(location_date, 1, 7)
)
SELECT
    m.month,
    COALESCE(r.reports, 0) AS reports,
    COALESCE(l.localizations, 0) AS localizations,
    COALESCE(r.reports, 0) - COALESCE(l.localizations, 0) AS net_backlog_flow,
    r.pct_all_reports_located_le_3d
FROM months m
LEFT JOIN reports r USING(month)
LEFT JOIN locs l USING(month);


-- ---------------------------------------------------------------------
-- Cohortes de reporte: pregunta (B). Para no penalizar cohortes recientes
-- (que no han tenido tiempo de "madurar"), cada umbral solo se calcula
-- sobre reportes cuya antigüedad observada ya alcanza ese umbral
-- (observed_days >= N). Esto es censura por la derecha aplicada a un
-- KPI simple; el análisis de supervivencia (vw_survival_input) es la
-- versión completa que además usa la información parcial de las
-- cohortes que aún no maduran.
-- ---------------------------------------------------------------------
-- CORREGIDO (ver CHANGELOG.md y src/config.py::EXTRACT_CUTOFF_DATE): el
-- corte ya NO se infiere como MAX(report_date, location_date). Ese
-- método se rompía con el caso ID 1138 (location_date = 2022-12-15,
-- ~15 meses después de su reporte y fuera de línea respecto a sus
-- vecinos por ID), que movía el corte del proyecto un mes completo sin
-- ninguna revisión. El literal de abajo (2022-11-15) es la fecha
-- documentada en src/config.py::EXTRACT_CUTOFF_DATE -- si cambia, debe
-- actualizarse en AMBOS lugares porque esta vista es SQL estático sin
-- templating desde Python.
DROP VIEW IF EXISTS vw_report_cohorts;
CREATE VIEW vw_report_cohorts AS
WITH cutoff AS (
    SELECT '2022-11-15' AS max_date
), base AS (
    SELECT
        v.*,
        c.max_date,
        julianday(c.max_date) - julianday(v.report_date) AS observed_days
    FROM vw_cases v
    CROSS JOIN cutoff c
    WHERE v.report_date IS NOT NULL
)
SELECT
    substr(report_date, 1, 7) AS report_month,
    COUNT(*) AS reports,
    SUM(is_located) AS located_by_status,
    ROUND(AVG(observed_days), 1) AS avg_observed_days,

    SUM(CASE WHEN observed_days >= 3 THEN 1 ELSE 0 END) AS matured_3d_denominator,
    ROUND(100.0 * SUM(
        CASE WHEN observed_days >= 3 AND report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(CASE WHEN observed_days >= 3 THEN 1 ELSE 0 END), 0), 2)
        AS pct_matured_reports_located_le_3d,

    SUM(CASE WHEN observed_days >= 7 THEN 1 ELSE 0 END) AS matured_7d_denominator,
    ROUND(100.0 * SUM(
        CASE WHEN observed_days >= 7 AND report_to_location_days BETWEEN 0 AND 7 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(CASE WHEN observed_days >= 7 THEN 1 ELSE 0 END), 0), 2)
        AS pct_matured_reports_located_le_7d,

    SUM(CASE WHEN observed_days >= 30 THEN 1 ELSE 0 END) AS matured_30d_denominator,
    ROUND(100.0 * SUM(
        CASE WHEN observed_days >= 30 AND report_to_location_days BETWEEN 0 AND 30 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(CASE WHEN observed_days >= 30 THEN 1 ELSE 0 END), 0), 2)
        AS pct_matured_reports_located_le_30d
FROM base
GROUP BY substr(report_date, 1, 7);


-- ---------------------------------------------------------------------
-- Insumo para el análisis de supervivencia (Kaplan-Meier) en Python.
-- Cada fila = un caso con tiempo de reporte válido; "duration_days" es el
-- tiempo hasta el evento (localización) o, si sigue abierto, hasta la
-- fecha de corte del extracto (censura por la derecha). "event"=1 si se
-- observó localización dentro de la ventana, 0 si está censurado.
-- ---------------------------------------------------------------------
-- CORREGIDO (ver CHANGELOG.md y src/config.py::EXTRACT_CUTOFF_DATE):
-- mismo cambio que en vw_report_cohorts -- ya no se infiere el corte
-- como MAX(report_date, location_date).
-- CORREGIDO (auditoría de consistencia del corte, ver CHANGELOG.md y
-- docs/METHODOLOGY.md §7.1): con un corte administrativo fijo, ningún
-- `location_date` POSTERIOR al corte puede tratarse como un evento
-- observado -- esa información no existiría todavía "al momento del
-- corte". El caso ID 1138 (case_key 1136), con `location_date`
-- 2022-12-15 (posterior al corte 2022-11-15), se contaba antes como
-- evento CON VIDA observado a los 464 días -- inconsistente con la
-- propia definición del corte. La condición
-- `date(v.location_date) <= date(c.max_date)` re-censura ese caso (y
-- cualquier otro con la misma condición) a la fecha de corte: pasa a
-- contarse como abierto/censurado, con duración = corte - reporte, en
-- vez de como evento observado más allá de la ventana de observación.
-- Verificado: es el único caso del extracto con `location_date`
-- posterior al corte.
DROP VIEW IF EXISTS vw_survival_input;
CREATE VIEW vw_survival_input AS
WITH cutoff AS (
    SELECT '2022-11-15' AS max_date
)
SELECT
    v.case_key,
    v.borough_missing,
    v.sex,
    v.age_group,
    CAST(strftime('%Y', v.report_date) AS INTEGER) AS report_year,
    CASE
        WHEN v.is_located = 1 AND v.report_to_location_days IS NOT NULL
             AND date(v.location_date) <= date(c.max_date)
            THEN v.report_to_location_days
        ELSE julianday(c.max_date) - julianday(v.report_date)
    END AS duration_days,
    CASE
        WHEN v.is_located = 1 AND v.report_to_location_days IS NOT NULL
             AND date(v.location_date) <= date(c.max_date) THEN 1
        ELSE 0
    END AS event_observed
FROM vw_cases v
CROSS JOIN cutoff c
WHERE v.valid_for_report_timeline = 1
  AND v.report_date IS NOT NULL;


-- =======================================================================
-- AMPLIACIÓN: desenlaces CON VIDA / SIN VIDA.
--
-- location_condition (columna original Condicion.localizacion) YA estaba
-- mapeada en src/ingest.py y documentada en docs/DATA_DICTIONARY.md, pero
-- no se usaba en ninguna vista analítica hasta esta ampliación. Solo
-- existe para casos con is_located=1 (verificado: 0 casos DESAPARECIDO
-- tienen location_condition no nulo, ver docs/METHODOLOGY.md).
--
-- IMPORTANTE (ver docs/METHODOLOGY.md, sección de desenlaces): location_date
-- es la fecha en que el caso se cerró administrativamente como localizado,
-- NO necesariamente la fecha de fallecimiento en los casos SIN VIDA. Estas
-- vistas y el análisis que las consume NUNCA deben usarse para afirmar
-- cuándo murió una persona ni que una búsqueda más rápida habría evitado
-- un desenlace SIN VIDA — solo miden asociación entre el tiempo hasta el
-- cierre del caso y el desenlace registrado al cierre.
-- =======================================================================

-- Panorama general de location_condition entre localizados, con el cruce
-- contra disponibilidad de fecha de localización (para la auditoría de
-- casos faltantes/inconsistentes).
DROP VIEW IF EXISTS vw_outcome_overview;
CREATE VIEW vw_outcome_overview AS
SELECT
    COUNT(*) AS total_localizados,
    SUM(CASE WHEN location_condition = 'CON VIDA' THEN 1 ELSE 0 END) AS con_vida,
    SUM(CASE WHEN location_condition = 'SIN VIDA' THEN 1 ELSE 0 END) AS sin_vida,
    SUM(CASE WHEN location_condition IS NULL THEN 1 ELSE 0 END) AS condicion_desconocida,
    SUM(CASE WHEN location_condition IS NOT NULL AND location_date IS NULL THEN 1 ELSE 0 END)
        AS condicion_conocida_sin_fecha,
    SUM(CASE WHEN location_condition IS NULL AND location_date IS NOT NULL THEN 1 ELSE 0 END)
        AS fecha_conocida_sin_condicion,
    SUM(CASE WHEN location_condition IS NOT NULL AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END)
        AS condicion_conocida_con_duracion_valida
FROM vw_cases
WHERE is_located = 1;


-- Desenlace por sexo, edad y alcaldía: sobre localizados con
-- location_condition conocida (CON VIDA o SIN VIDA), sin exigir además
-- duración válida (ver §11 de outputs/FINAL_FINDINGS.md para la
-- justificación de este denominador más amplio). El intervalo de
-- confianza (Wilson) y el umbral de N≥30 se calculan en
-- src/outcomes.py, igual que below_min_sample_size en analysis.py.
DROP VIEW IF EXISTS vw_outcome_sex_kpis;
CREATE VIEW vw_outcome_sex_kpis AS
SELECT
    sex,
    COUNT(*) AS n_analitico,
    SUM(CASE WHEN location_condition = 'SIN VIDA' THEN 1 ELSE 0 END) AS sin_vida_n
FROM vw_cases
WHERE is_located = 1 AND location_condition IS NOT NULL AND sex IS NOT NULL
GROUP BY sex;

DROP VIEW IF EXISTS vw_outcome_age_group_kpis;
CREATE VIEW vw_outcome_age_group_kpis AS
SELECT
    age_group,
    COUNT(*) AS n_analitico,
    SUM(CASE WHEN location_condition = 'SIN VIDA' THEN 1 ELSE 0 END) AS sin_vida_n
FROM vw_cases
WHERE is_located = 1 AND location_condition IS NOT NULL AND age_group IS NOT NULL
GROUP BY age_group;

DROP VIEW IF EXISTS vw_outcome_borough_kpis;
CREATE VIEW vw_outcome_borough_kpis AS
SELECT
    borough_missing,
    COUNT(*) AS n_analitico,
    SUM(CASE WHEN location_condition = 'SIN VIDA' THEN 1 ELSE 0 END) AS sin_vida_n
FROM vw_cases
WHERE is_located = 1 AND location_condition IS NOT NULL AND borough_missing IS NOT NULL
GROUP BY borough_missing;


-- Desenlace por intervalo de tiempo, reloj REPORTE->LOCALIZACIÓN. Solo
-- casos con duración válida en ese reloj (valid_for_report_timeline=1);
-- los excluidos se documentan aparte en outcome_intervals_exclusions.csv
-- (src/outcomes.py), con el mismo criterio ya usado en vw_kpi_overview.
DROP VIEW IF EXISTS vw_outcome_interval_report;
CREATE VIEW vw_outcome_interval_report AS
SELECT
    CASE
        WHEN report_to_location_days <= 1 THEN '1_≤1 día'
        WHEN report_to_location_days <= 3 THEN '2_>1-3 días'
        WHEN report_to_location_days <= 7 THEN '3_>3-7 días'
        WHEN report_to_location_days <= 30 THEN '4_>7-30 días'
        ELSE '5_>30 días'
    END AS interval_bucket,
    COALESCE(location_condition, 'DESCONOCIDA') AS location_condition,
    COUNT(*) AS n
FROM vw_cases
WHERE is_located = 1 AND valid_for_report_timeline = 1
GROUP BY interval_bucket, COALESCE(location_condition, 'DESCONOCIDA');


-- Igual que la anterior, pero con el reloj DESAPARICIÓN->LOCALIZACIÓN
-- (missing_to_location_days), que sí incluye los casos localizados antes
-- del registro del reporte (ver §3 de outputs/FINAL_FINDINGS.md).
DROP VIEW IF EXISTS vw_outcome_interval_missing;
CREATE VIEW vw_outcome_interval_missing AS
SELECT
    CASE
        WHEN missing_to_location_days <= 1 THEN '1_≤1 día'
        WHEN missing_to_location_days <= 3 THEN '2_>1-3 días'
        WHEN missing_to_location_days <= 7 THEN '3_>3-7 días'
        WHEN missing_to_location_days <= 30 THEN '4_>7-30 días'
        ELSE '5_>30 días'
    END AS interval_bucket,
    COALESCE(location_condition, 'DESCONOCIDA') AS location_condition,
    COUNT(*) AS n
FROM vw_cases
WHERE is_located = 1 AND valid_for_missing_timeline = 1
GROUP BY interval_bucket, COALESCE(location_condition, 'DESCONOCIDA');


-- Insumo para el modelo de riesgos competitivos (Aalen-Johansen, en
-- src/outcomes.py). A diferencia de vw_survival_input (que trata "estar
-- localizado" como un solo evento), aquí se distingue el TIPO de evento:
-- un caso puede terminar CON VIDA, SIN VIDA, localizado con condición
-- desconocida, o seguir abierto (censurado). Tratar cada desenlace por
-- separado con Kaplan-Meier simple (evento=SIN VIDA, censurando todo lo
-- demás) sobreestima su incidencia porque ignora que el otro desenlace
-- "consume" población en riesgo; ver docs/METHODOLOGY.md para la
-- comparación numérica entre el método ingenuo y el correcto.
-- `location_date` se expone aquí (no solo report_to_location_days) para
-- que src/outcomes.py pueda aplicar la misma re-censura por consistencia
-- de corte que vw_survival_input: ningún location_date posterior a
-- EXTRACT_CUTOFF_DATE puede tratarse como evento observado (ver
-- CHANGELOG.md y docs/METHODOLOGY.md §7.1). event_type aquí todavía NO
-- aplica esa regla -- se calcula en Python porque el corte es una
-- constante de src/config.py, no un literal SQL adicional que haya que
-- mantener sincronizado en un tercer lugar.
DROP VIEW IF EXISTS vw_outcome_competing_risk_input;
CREATE VIEW vw_outcome_competing_risk_input AS
SELECT
    case_key,
    report_date,
    location_date,
    is_located,
    report_to_location_days,
    location_condition,
    CASE
        WHEN is_located = 1 AND report_to_location_days IS NOT NULL AND location_condition = 'CON VIDA' THEN 1
        WHEN is_located = 1 AND report_to_location_days IS NOT NULL AND location_condition = 'SIN VIDA' THEN 2
        WHEN is_located = 1 AND report_to_location_days IS NOT NULL THEN 3  -- localizado, condición desconocida
        ELSE 0  -- censurado: sigue abierto
    END AS event_type
FROM vw_cases
WHERE valid_for_report_timeline = 1
  AND report_date IS NOT NULL;
