# Medidas DAX

Ver `POWER_BI_GUIDE.md` sección 3 para el detalle y las notas de uso.
Medidas base sobre `fact_cases`:

```DAX
Total Reportes = COUNTROWS(fact_cases)
```

```DAX
Total Localizados = CALCULATE(COUNTROWS(fact_cases), fact_cases[is_located] = 1)
```

```DAX
Casos Abiertos = [Total Reportes] - [Total Localizados]
```

```DAX
% Abiertos = DIVIDE([Casos Abiertos], [Total Reportes])
```

```DAX
Localizados con duración válida =
CALCULATE(
    COUNTROWS(fact_cases),
    fact_cases[valid_for_report_timeline] = 1,
    fact_cases[is_located] = 1
)
```

```DAX
% Localizado ≤3d (entre localizados) =
VAR Numerador =
    CALCULATE(
        COUNTROWS(fact_cases),
        fact_cases[report_to_location_days] >= 0,
        fact_cases[report_to_location_days] <= 3
    )
RETURN DIVIDE(Numerador, [Localizados con duración válida])
```

Para indicadores ya agregados por alcaldía/sexo/edad/año, usar
directamente los campos de `borough_kpis` / `sex_kpis` /
`age_group_kpis` / `year_kpis` en vez de recalcular con DAX: evita que
dos motores de cálculo (DAX y el pipeline Python/SQL) diverjan por
redondeo o por una definición de población ligeramente distinta.

Para el % estimado que sí considera a los casos abiertos (pregunta B),
usar `survival_kpis` importado tal cual — la lógica de censura de
Kaplan-Meier no se reimplementa en DAX.

> Importante: no mezclar `% localizado dentro de 72h entre casos
> localizados` con `% de todos los reportes localizado dentro de 72h`
> (estimado por supervivencia). Son indicadores distintos — ver
> `docs/METHODOLOGY.md` sección 3.
