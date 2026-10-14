# Contenedor de servicios

## Descripción general

El contenedor asigna contratos o alias a implementaciones y crea grafos desde anotaciones de tipo. Admite instancias preparadas, servicios transient, singletons de proceso y servicios scoped locales al contexto. `build` construye una clase, `invoke` inyecta una función y `call` inyecta un método nombrado.

El código de aplicación suele interactuar mediante `Application`, que extiende el contenedor; autores del framework definen `ServiceProvider` y fachadas. Providers diferidos posponen imports/registro hasta solicitar un contrato. Kernels HTTP/console crean scopes para impedir fugas de dependencias locales.

## Requisitos

- Python 3.14 o posterior.
- Sin dependencia opcional ni servicio externo.
- Anotaciones runtime en parámetros inyectables.
- Un contexto `beginScope()` activo antes de resolver un binding `scoped`.
- Referencias adelantadas resolubles en el módulo del callable.

## Recorrido del módulo

- [Registrar e invocar servicios](bindings-and-invocation.md)
- [Service Providers, facades y extensión](providers-and-facades.md)
- [Scopes, aislamiento y concurrencia](scopes-and-concurrency.md)

Continúa por: [foundation](../../../foundation/docs/es/README.md) · [schemas](../../../schemas/docs/es/README.md).

Los ejemplos que requieren bootstrap, una solicitud o servicios externos indican su contexto. Los resultados de comprobación de esta reconstrucción se distinguen de las notas históricas; no se presupone que se haya ejecutado una integración de producción.
