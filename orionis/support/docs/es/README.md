# Tipos y utilidades de soporte

## Descripción general

`orionis.support` es la capa compartida de utilidades de Orionis. Contiene las fachadas para acceder a servicios del framework, tipos auxiliares orientados a valores, serialización de entidades, estructuras inmutables, metaclases reutilizables, formateo de excepciones, medición de tiempo, dimensionamiento de workers y el proveedor integrado de citas inspiradoras.

El paquete tiene deliberadamente dos niveles de API. `orionis.support.facades` y `orionis.support.types` ofrecen importaciones seleccionadas; los auxiliares de menor nivel se importan desde sus módulos de definición. El paquete raíz `orionis.support` no reexporta estos objetos.

## Requisitos

- Python 3.14 o posterior.
- El runtime de Orionis y sus dependencias declaradas. Este módulo usa directamente `pendulum`, `dotty-dict` y `psutil`.
- Una aplicación Orionis inicializada antes de invocar fachadas respaldadas por servicios. `DateTime` es una clase autónoma y no requiere el contenedor para las operaciones de fecha normales.

## Recorrido del módulo

- [Transformar colecciones y cadenas](collections-and-strings.md)
- [Entidades y estructuras de datos](entities-and-structures.md)
- [Facades, fechas y utilidades del runtime](facades-and-runtime-utilities.md)

Continúa por: [container](../../../container/docs/es/README.md) · [schemas](../../../schemas/docs/es/README.md).

Los ejemplos que requieren bootstrap, una solicitud o servicios externos indican su contexto. Los resultados de comprobación de esta reconstrucción se distinguen de las notas históricas; no se presupone que se haya ejecutado una integración de producción.
