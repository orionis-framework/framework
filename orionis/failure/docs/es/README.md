# Gestión de excepciones

## Descripción general

`Catch` es el servicio exportado por el paquete: recibe una excepción, resuelve perezosamente el handler de aplicación, reporta y despacha el renderizado según el kernel del scope activo. Console usa `handleCLI`; HTTP usa `handleHTTP`; contextos desconocidos solo reportan.

`BaseExceptionHandler` aporta la política predeterminada: conversión a `Throwable`, logging, render CLI, mapeo de estados HTTP, respuestas 500 saneadas en producción y detalle en debug. La aplicación puede registrar otro handler que satisfaga `IBaseExceptionHandler`.

## Requisitos

- Python 3.14 o posterior.
- Aplicación/contenedor Orionis iniciado para `Catch.exception()` o la fachada `Catch`.
- Scope activo con contexto `kernel`.
- Request o adaptador de transporte al manejar una excepción HTTP.
- Servicios de logging, consola y respuestas resolubles para el método elegido.

## Recorrido del módulo

- [Reportar y gestionar excepciones](handling-exceptions.md)
- [Políticas de errores y referencia](policies-and-reference.md)

Continúa por: [http](../../../http/docs/es/README.md) · [logging](../../../logging/docs/es/README.md).

Los ejemplos que requieren bootstrap, una solicitud o servicios externos indican su contexto. Los resultados de comprobación de esta reconstrucción se distinguen de las notas históricas; no se presupone que se haya ejecutado una integración de producción.
