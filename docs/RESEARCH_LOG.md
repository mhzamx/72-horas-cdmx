# Registro de investigación previa

## Pregunta de originalidad

Antes de construir el análisis se revisaron antecedentes para evitar presentar como novedoso un estudio ya publicado.

### Antecedente cercano identificado

**Aguilar-Velázquez et al. (2025), PLOS ONE — “Understanding disappearances in Mexico City: A data-driven analysis”.**

El estudio utiliza el mismo registro interno histórico de la CBPCDMX, pero su objetivo principal es caracterizar perfiles, concentración territorial, desigualdad, narcomenudeo y clustering de alcaldías.

### Diferencia de 72 HORAS

Este proyecto no replica ese objetivo. Su unidad analítica central es el **tiempo del proceso observado**:

- hechos → reporte;
- reporte → localización;
- resolución temprana;
- casos todavía abiertos mediante supervivencia;
- flujo reportes vs localizaciones;
- señales descriptivas de presión operativa;
- auditoría explícita de calidad temporal.

## Fuentes documentales

1. CBPCDMX — Versión Pública del Registro Interno de Personas Desaparecidas  
   https://comisiondebusqueda.cdmx.gob.mx/CBP/rpd/version-publica

2. Comisión de Derechos Humanos de la Ciudad de México — Guía técnica sobre búsqueda de personas (2024). Documenta una tabla Excel con corte al 30/06/2023.

3. Aguilar-Velázquez, D. et al. (2025). PLOS ONE 20(9): e0323405.  
   https://doi.org/10.1371/journal.pone.0323405

4. Actualización del Protocolo Homologado para la Búsqueda de Personas Desaparecidas y No Localizadas (2025/2026): la lógica normativa es de búsqueda inmediata; el nombre “72 HORAS” no debe interpretarse como periodo de espera.

## Actualización: archivo oficial obtenido y verificado

Se obtuvo `data/raw/registro-interno-cbp-15-noviembre.xlsx` (2,958 filas,
21 columnas), verificado columna por columna contra la descripción
pública de la CBPCDMX (ver `docs/SOURCE_ACCESS.md` y
`docs/DATA_DICTIONARY.md`). Su ventana real (`report_date` 2019-06-25 a
2022-11-14) es distinta tanto del corte 30/06/2023 documentado en la
guía técnica de 2024 como del extracto de 3,450 filas (2019–2023) del
estudio de PLOS ONE: es un corte oficial más antiguo del mismo registro.
A partir de este punto, `outputs/FINAL_FINDINGS.md` contiene resultados
reales (ya no una auditoría pendiente de datos).
