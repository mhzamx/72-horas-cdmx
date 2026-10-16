# Resumen ejecutivo — 72 HORAS (v0.2 final)

## Qué investigamos

Qué proporción de las personas reportadas como desaparecidas ante la
Comisión de Búsqueda de Personas de la Ciudad de México (CBPCDMX) tiene
localización documentada dentro de los primeros 3 días posteriores al
reporte, y qué características registradas se asocian —no necesariamente
como causa— con una localización más rápida o más lenta. Usamos el
registro público oficial de la propia Comisión: 2,958 casos reportados
entre el 25 de junio de 2019 y el 14 de noviembre de 2022.

## Qué encontramos

- Al corte del registro (15 de noviembre de 2022), 1,777 casos (60.1%)
  tenían estatus de localizado y 1,181 (39.9%) seguían abiertos.
- **Estimación principal: 44.2%** (IC 95% 42.3–46.2%) de los casos
  recibidos tenía localización documentada a 3 días calendario o menos
  del reporte (población de 2,937 casos; se excluyen 21 con un orden de
  fechas imposible). A 30 días, 56.8%.
- **La cifra depende de cómo se traten los datos incompletos.** Según
  cómo se consideren los 227 casos localizados sin fecha, el resultado va
  de 38.5% a 46.2%. La versión anterior de este análisis reportaba 34.0%
  porque dejaba fuera 564 casos localizados: 318 localizados antes de que
  se registrara el reporte, 227 sin fecha de localización y 19 con orden
  de fechas imposible. La estimación principal incluye a los 318 (como
  día 0) y a los 227 (con imputación múltiple).
- **Con vida y sin vida.** A 3 días: 40.7% con vida y 3.1% sin vida. A 30
  días: 51.8% con vida, 4.4% sin vida y 0.6% con desenlace desconocido.
  La fecha de localización es la registrada: no es fecha de fallecimiento
  y la fuente no documenta a qué momento del proceso corresponde.
- **Características (asociación, no causa).**
  - Mujeres 48.6% frente a hombres 41.4%; los intervalos de confianza no
    se traslapan.
  - Por edad, 60 años o más tiene la proporción más alta (55.4%); los
    grupos de 0-11, 30-44 y 45-59 años quedan alrededor de 39-40%.
  - Por año, 2022 es el más bajo (32.9%), lo que puede reflejar rezago en
    la actualización del estatus.
  - Por alcaldía, los intervalos son amplios y se traslapan, por lo que no
    se presenta ranking. Los casos sin alcaldía registrada tienen la
    proporción más baja (25.6%).

## Qué significa

Con los mismos registros, la proporción de casos con localización
documentada en los primeros días cambia hasta ~12 puntos según cómo se
traten los casos abiertos, los localizados antes del registro y las
fechas faltantes. Cualquier cifra de este tipo debe declarar esas
decisiones. Mirar solo a los casos ya resueltos hace parecer al sistema
más rápido de lo que es; excluir localizados sin revisarlos lo hace
parecer más lento.

72 horas es un hito de medición, no un plazo de espera: la búsqueda debe
iniciar de inmediato.

## Qué NO podemos concluir

- No podemos decir que una alcaldía, sexo o grupo de edad *cause* una
  localización más rápida o más lenta: solo observamos asociación en
  datos agregados, sin controlar por tipo de caso, recursos disponibles u
  otros factores.
- No podemos hablar de "72 horas exactas": la fuente registra fechas, no
  horas, así que medimos días calendario (≤3 días).
- No podemos distinguir una desaparición prolongada de un estatus no
  actualizado: 43.7% de los reportes de 2019 y 50.8% de los de 2022
  seguían abiertos al corte.
- No cubrimos lo ocurrido después de noviembre de 2022: es el corte real
  de este extracto.
- No evaluamos la calidad de las diligencias de búsqueda, solo el tiempo
  entre las fechas que capturó el registro.

## Por qué importa

Distinguir entre "qué tan rápido se localizan los casos que sí se
localizan" y "qué proporción del total de casos reportados tiene
localización documentada" cambia la lectura de cómo funciona el proceso
de búsqueda. Este proyecto muestra cómo llegar a esa segunda cifra con
herramientas estándar (SQL, Python, análisis de supervivencia, riesgos
competitivos e imputación múltiple) y cómo comunicar su incertidumbre
sin exagerar ni minimizar lo que los datos permiten decir.

Detalle y denominadores: `outputs/FINAL_FINDINGS.md` §18 y
`docs/METHODOLOGY.md` §13. Tablero: `powerbi/72HORAS_v02_final.pdf`.
