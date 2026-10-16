# Resumen ejecutivo — 72 HORAS

## Qué investigamos

Qué tan rápido se localiza a una persona reportada como desaparecida en
Ciudad de México después de que el caso llega a la Comisión de Búsqueda
de Personas (CBPCDMX), y qué factores están asociados —no necesariamente
como causa— con una localización más rápida o más lenta. Usamos el
registro público oficial de la propia Comisión: 2,958 casos reportados
entre el 25 de junio de 2019 y el 14 de noviembre de 2022.

## Qué encontramos

De cada 10 reportes de este periodo, 6 ya estaban marcados como
localizados al momento del corte y 4 seguían abiertos. Entre los casos
ya localizados, la mitad se resolvió en apenas 1 día y 2 de cada 3 en 3
días o menos — pero una parte se estira mucho más (hasta más de 50 días
en el 5% más lento). Esa mezcla de "casos rápidos" y "cola larga" es
justo lo que hace que un solo promedio sea engañoso.

Cuando se toma en cuenta que 4 de cada 10 casos seguían sin resolver, la
estimación honesta de "% ya localizado a los 3 días" no es 67% (la
cifra que sale de mirar solo a los ya localizados), sino cerca de 34%.
La diferencia entre esas dos cifras es, en sí misma, uno de los
hallazgos más importantes del proyecto: mirar solo a los casos
resueltos hace parecer al sistema más rápido de lo que realmente es.

También encontramos que "la persona fue encontrada antes de que el
reporte quedara registrado" es un patrón real (más de 300 casos), no un
error de captura como podría parecer a primera vista — y lo separamos
explícitamente de los pocos casos (21) donde el orden de las fechas sí
es imposible.

Por alcaldía, la velocidad de resolución entre localizados varía de
61.5% a 78.9% en ≤3 días (comparando solo alcaldías con al menos 30
casos analíticos). Por sexo, no hay diferencia relevante en velocidad
de resolución. Por edad, adolescentes de 12 a 17 años muestran la
resolución más lenta entre localizados y personas mayores de 60 la más
rápida. Identificamos también 2 meses puntuales (diciembre 2019 y mayo
2021) donde un pico de reportes coincidió con un deterioro de la
velocidad de resolución frente a la tendencia reciente, calculado solo
sobre los meses dentro de la ventana real de reportes.

## Qué significa

El sistema resuelve una fracción importante de los casos muy rápido,
pero una fracción también importante permanece sin resolver más allá de
30 días — y una parte de ese grupo simplemente sigue abierta al momento
en que se corta cualquier análisis, lo cual siempre subestimará el
tiempo real que tomará resolverse. Cualquier reporte de este tipo de
datos que no distinga entre "% entre los ya resueltos" y "% del total,
incluyendo lo que sigue abierto" corre el riesgo de sobrestimar qué tan
rápido funciona el sistema.

## Qué NO podemos concluir

- No podemos decir que una alcaldía, sexo o grupo de edad *cause* una
  resolución más lenta: solo observamos asociación en datos agregados,
  sin controlar por tipo de caso, recursos disponibles u otros factores.
- No podemos hablar de "72 horas exactas": la fuente registra fechas,
  no horas, así que medimos días calendario.
- No cubrimos lo ocurrido después de noviembre de 2022: es el corte
  real de este extracto.
- No evaluamos la calidad de las diligencias de búsqueda en sí, solo
  el tiempo observado entre las fechas que capturó el registro.
- Los pocos meses con "señal de presión operativa" son una alerta
  descriptiva para revisar, no una prueba de que algo falló.

## Por qué importa

Entender la diferencia entre "qué tan rápido se resuelven los casos que
sí se resuelven" y "qué tan rápido se resuelve el total de los casos
reportados" no es un detalle técnico: cambia la lectura de qué tan bien
está funcionando el proceso de búsqueda. Este proyecto muestra cómo
llegar a esa segunda cifra —la más honesta— con herramientas estándar
de análisis de datos (SQL, Python, supervivencia), y cómo comunicar la
diferencia sin exagerar ni minimizar lo que los datos permiten decir.
