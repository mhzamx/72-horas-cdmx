-- 72 HORAS: consultas de portafolio.
-- Se ejecutan sobre data/processed/72_horas.db (tablas cases_raw,
-- quality_flags, y las vistas de sql/02_views.sql).
-- Pensadas para poder explicarse línea por línea en una entrevista.

-- =====================================================================
-- 1) KPI principales del proyecto (una sola fila, para un resumen).
-- =====================================================================
SELECT * FROM vw_kpi_overview;


-- =====================================================================
-- 2) Alcaldías con menor % de localización en ≤72h, SOLO entre las que
--    tienen muestra suficiente (WHERE + agregación + HAVING).
--    Evita el error clásico de "ranking con N chico" (ver METHODOLOGY.md).
-- =====================================================================
SELECT
    borough_missing,
    sample_size,
    located_records,
    open_records,
    pct_located_le_3d_among_located,
    avg_report_to_location_days
FROM vw_borough_kpis
WHERE sample_size >= 30
ORDER BY pct_located_le_3d_among_located ASC;


-- =====================================================================
-- 3) RANKING de alcaldías por velocidad de resolución, con dos técnicas
--    de ranking (RANK deja huecos ante empates; DENSE_RANK no).
--    Demuestra window functions con PARTITION/ORDER BY.
-- =====================================================================
SELECT
    borough_missing,
    sample_size,
    pct_located_le_3d_among_located,
    RANK()       OVER (ORDER BY pct_located_le_3d_among_located DESC) AS rank_con_huecos,
    DENSE_RANK() OVER (ORDER BY pct_located_le_3d_among_located DESC) AS rank_sin_huecos
FROM vw_borough_kpis
WHERE sample_size >= 30
ORDER BY pct_located_le_3d_among_located DESC;


-- =====================================================================
-- 4) Cohortes mensuales de reporte (pregunta B: % ya localizado dentro
--    del umbral, considerando también los casos aún abiertos, solo entre
--    cohortes ya "maduras" para ese umbral).
-- =====================================================================
SELECT
    report_month,
    reports,
    matured_3d_denominator,
    pct_matured_reports_located_le_3d
FROM vw_report_cohorts
ORDER BY report_month;


-- =====================================================================
-- 5) Casos con problemas de calidad temporal, clasificados por tipo
--    (JOIN entre la tabla de hechos y la tabla de flags).
-- =====================================================================
SELECT
    c.case_key,
    c.report_date,
    c.missing_date,
    c.location_date,
    q.location_before_report,
    q.location_before_event,
    q.report_before_event,
    q.status_located_without_location_date,
    q.duplicate_content,
    q.historic_missing_date
FROM cases_raw c
JOIN quality_flags q USING(case_key)
WHERE q.location_before_report = 1
   OR q.location_before_event = 1
   OR q.report_before_event = 1
   OR q.status_located_without_location_date = 1
   OR q.duplicate_content = 1
   OR q.historic_missing_date = 1;


-- =====================================================================
-- 6) Distribución por sexo (CASE + agregación), con el mismo denominador
--    documentado que el resto del proyecto (localizados con duración
--    válida, no "todos los que dicen LOCALIZADO").
-- =====================================================================
SELECT
    sex,
    sample_size,
    located_records,
    located_with_valid_duration,
    pct_located_le_3d_among_located
FROM vw_sex_kpis
ORDER BY sample_size DESC;


-- =====================================================================
-- 7) Cambio mensual de volumen de reportes: window function LAG() para
--    comparar cada mes contra el anterior (CTE + window function).
-- =====================================================================
WITH monthly AS (
    SELECT
        substr(report_date, 1, 7) AS month,
        COUNT(*) AS reports
    FROM vw_cases
    WHERE report_date IS NOT NULL
    GROUP BY substr(report_date, 1, 7)
)
SELECT
    month,
    reports,
    LAG(reports) OVER (ORDER BY month) AS previous_month,
    reports - LAG(reports) OVER (ORDER BY month) AS absolute_change,
    ROUND(
        100.0 * (reports - LAG(reports) OVER (ORDER BY month))
        / NULLIF(LAG(reports) OVER (ORDER BY month), 0),
        2
    ) AS pct_change
FROM monthly
ORDER BY month;


-- =====================================================================
-- 8) Promedio móvil de 6 meses del volumen de reportes, con una window
--    function de marco explícito (ROWS BETWEEN). Sirve para ver
--    tendencia sin el ruido mes a mes; es la base de la señal de presión
--    operativa que se calcula con más detalle en Python (más fácil de
--    leer con pandas.rolling, pero aquí se muestra que también se puede
--    hacer en SQL puro).
-- =====================================================================
WITH monthly AS (
    SELECT
        substr(report_date, 1, 7) AS month,
        COUNT(*) AS reports
    FROM vw_cases
    WHERE report_date IS NOT NULL
    GROUP BY substr(report_date, 1, 7)
)
SELECT
    month,
    reports,
    ROUND(AVG(reports) OVER (
        ORDER BY month
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    ), 1) AS reports_avg_6m
FROM monthly
ORDER BY month;


-- =====================================================================
-- 9) Top-3 alcaldías con más volumen dentro de cada año de reporte
--    (window function PARTITION BY + ROW_NUMBER, patrón "top-N por
--    grupo" muy común en entrevistas).
-- =====================================================================
WITH by_year_borough AS (
    SELECT
        CAST(strftime('%Y', report_date) AS INTEGER) AS report_year,
        borough_missing,
        COUNT(*) AS reports
    FROM vw_cases
    WHERE report_date IS NOT NULL AND borough_missing IS NOT NULL
    GROUP BY report_year, borough_missing
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY report_year ORDER BY reports DESC
        ) AS rn
    FROM by_year_borough
)
SELECT report_year, borough_missing, reports
FROM ranked
WHERE rn <= 3
ORDER BY report_year, rn;


-- =====================================================================
-- 10) Grupo de edad x sexo: tabla cruzada de volumen y % localizado en
--     ≤72h, con HAVING para exigir tamaño mínimo de muestra en la
--     combinación (no solo en cada dimensión por separado).
-- =====================================================================
SELECT
    age_group,
    sex,
    COUNT(*) AS sample_size,
    SUM(is_located) AS located_records,
    ROUND(100.0 * SUM(
        CASE WHEN report_to_location_days BETWEEN 0 AND 3 THEN 1 ELSE 0 END
    ) / NULLIF(SUM(
        CASE WHEN is_located = 1 AND valid_for_report_timeline = 1 THEN 1 ELSE 0 END
    ), 0), 2) AS pct_located_le_3d_among_located
FROM vw_cases
WHERE age_group IS NOT NULL AND sex IS NOT NULL
GROUP BY age_group, sex
HAVING COUNT(*) >= 30
ORDER BY age_group, sex;
