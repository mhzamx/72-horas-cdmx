-- 72 HORAS: esquema base sobre las tablas cargadas por src/database.py
-- (cases_raw = capa "cleaned": tipos correctos, placeholders normalizados,
--  pero SIN filas eliminadas; quality_flags = resultado de src/quality.py).

DROP TABLE IF EXISTS analysis_meta;

CREATE TABLE analysis_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_cases_report_date
ON cases_raw(report_date);

CREATE INDEX IF NOT EXISTS idx_cases_missing_date
ON cases_raw(missing_date);

CREATE INDEX IF NOT EXISTS idx_cases_location_date
ON cases_raw(location_date);

CREATE INDEX IF NOT EXISTS idx_cases_borough
ON cases_raw(borough_missing);

CREATE INDEX IF NOT EXISTS idx_cases_status
ON cases_raw(status);

CREATE INDEX IF NOT EXISTS idx_cases_sex
ON cases_raw(sex);

CREATE INDEX IF NOT EXISTS idx_quality_case_key
ON quality_flags(case_key);
