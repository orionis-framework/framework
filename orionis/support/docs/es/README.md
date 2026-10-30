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

## Ejecución acotada y rendimiento

Importa `threaded` y `BoundedExecutor` desde `orionis.support.concurrency`. Decora un manejador síncrono bloqueante con `@threaded` para ejecutarlo fuera del loop conservando su firma de inyección y copiando las variables de contexto. El pool compartido admite cuatro llamadas activas y 32 pendientes. Sus dependencias deben admitir acceso desde threads; el trabajo CPU de Python sigue compitiendo por el GIL. Los manejadores síncronos ordinarios conservan su ejecución anterior.

`BoundedExecutor(workers, max_pending=capacity)` permite definir el presupuesto de trabajo de la aplicación. `await pool.run(callback, *args)` lanza `WorkQueueFullError` inmediatamente al llenarse. Define explícitamente la respuesta de sobrecarga. Cancelar trabajo pendiente evita ejecutarlo; cancelar trabajo activo espera su finalización nativa antes de liberar capacidad. Las llamadas nativas necesitan su propio timeout de I/O finito. Cierra los pools propios con `await pool.aclose()`.

`Collection.unique()` indexa listas, diccionarios y conjuntos incorporados anidados en tiempo esperado lineal respecto al tamaño total de entrada. Las entradas pequeñas no hashables (hasta 128 elementos) conservan el recorrido por igualdad, de menor costo a esa escala. Los objetos arbitrarios no hashables y los ciclos también conservan la comparación por igualdad. Usa una identidad de negocio hashable con `collection.unique(lambda item: item.identifier)` para evitar ese recorrido. La variante con clave conserva el primer representante, incluso si el campo contiene listas o diccionarios.
