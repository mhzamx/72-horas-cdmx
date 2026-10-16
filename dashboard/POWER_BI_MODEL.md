# Modelo de Power BI

Ver `POWER_BI_GUIDE.md` para la guía completa (importación, relaciones,
DAX, páginas, filtros). Este archivo es el resumen rápido del modelo.

## Tablas del esquema en estrella (`dashboard/data/`)

- `fact_cases` — un renglón por caso; incluye llaves de fecha
  (`report_date_key`, `missing_date_key`, `location_date_key`), la
  alcaldía, sexo, grupo de edad y todos los flags de calidad.
- `dim_date` — calendario completo cubierto por los datos.
- `dim_borough` — una fila por alcaldía, con `sample_size` y
  `below_min_sample_size` ya calculados.

## Tablas de agregados (`outputs/tables/`, se importan sin relacionar)

`kpi_overview`, `borough_kpis`, `sex_kpis`, `age_group_kpis`,
`year_kpis`, `monthly_flow`, `cohort_resolution`, `survival_curve`,
`survival_by_sex`, `survival_by_borough_missing`,
`survival_by_age_group`, `pressure_signals`, `data_quality_summary`.

## Páginas

1. Resumen ejecutivo / 72 horas
2. Geografía / alcaldías
3. Tiempo y cohortes
4. Calidad y metodología

Detalle de visuales por página en `POWER_BI_GUIDE.md`.
