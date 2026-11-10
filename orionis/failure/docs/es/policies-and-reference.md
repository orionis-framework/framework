# Políticas de errores y referencia

## API pública

### Contrato del handler de aplicación

`IBaseExceptionHandler`, disponible en `orionis.failure.contracts.handler`, declara dos métodos async abstractos:

| Método | Retorno | Responsabilidad |
|---|---|---|
| `handleFailure(exception, context)` | `FailureHandling \| None` | Recibir la excepción original y seleccionar efectos diferidos una vez por incidente. |
| `handleResult(value, context)` | `FailureHandling \| None` | Recibir un resultado declarado fallido sin fabricar una excepción. |

`BaseExceptionHandler` implementa ambos. Su `handleFailure` retorna un plan que conserva logging y presentación HTTP/CLI predeterminados; su `handleResult` retorna `None`. El helper `toThrowable(exception)` convierte argumentos a texto y conserva el traceback nativo. `isExceptionIgnored(exception)` comprueba la clase exacta en `dont_catch` y rechaza valores que no sean excepciones con `TypeError`.

### `FailureHandling`

Se importa desde `orionis.failure.entities`. Es un plan mutable por incidente, separado del contexto y los recibos inmutables.

| Miembro | Significado |
|---|---|
| `logging` | Callback async opcional sin argumentos. El runtime es dueño de su ejecución. |
| `presentation` | Callback async opcional que acepta los argumentos por nombre `flow` y `request=None`. El propietario del protocolo solicita su ejecución. |
| `complete()` | Ejecuta logging una vez; el éxito marca `reported=True`. Las llamadas repetidas no reintentan un callback fallido. |
| `present(*, flow, request=None)` | Ejecuta presentación una vez y conserva su resultado o fallo. |
| `reported`, `degraded` | Estado del manejo del plan. Los recibos del runtime exponen el estado de entrega sin retener el plan ni la excepción. |

El handler selecciona callbacks y retorna el plan. Las protecciones de reporte del runtime rodean su finalización; `complete()` no es un mecanismo independiente de reporte de emergencia. La presentación espera a que el propietario de la ejecución disponga del request vivo. No guardes planes en atributos del singleton ni los conserves entre incidentes independientes.

### Contexto, recibo y throwable

`FailureContext`, `FailureReceipt` y `Throwable` se exportan desde `orionis.failure.entities`.

- `FailureContext` es inmutable y contiene flujo, fase, operación, identificadores de correlación e incidente, `expected`, `reporting_allowed` y metadatos escalares acotados. No retiene objetos de transporte. El runtime deshabilita `reporting_allowed` cuando comienzan a cerrarse los recursos de reporte.
- `FailureReceipt` contiene `event_id`, `delivered`, `reported`, `duplicate` y `degraded`. Entrega no implica logging: los fallos esperados, ignorados o de recepción sin efectos pueden entregarse sin un registro ERROR.
- `Throwable` es una dataclass congelada, keyword-only y slotted, con `classtype`, `message`, `args` como texto y `traceback` nativo opcional. No se serializa ni formatea por sí sola.

### Catch, fachada y helpers del runtime

`Catch` se exporta desde `orionis.failure`; `ICatch`, desde `orionis.failure.contracts`. Las aplicaciones suelen recibir `ICatch` por inyección o usar `orionis.support.facades.Catch`. `CatchProvider` vincula el servicio singleton y fija la fachada.

`Catch.exception(exception, request=None)` lee `kernel` del scope activo, captura el incidente y solicita presentación HTTP/CLI a su plan. Reutiliza el estado del incidente existente sin otra llamada al hook de aplicación. `Catch.capture(exception, *, context)` no requiere scope ni solicita presentación.

`capture`, `capture_result` y `operation` están disponibles en `orionis.failure.runtime`. Capturar requiere un runtime activo después del inicio. Los propietarios notifican fallos explícitamente y conservan sus respuestas, reintentos, recuperación y propagación. Un plan personalizado de resultado puede registrar, pero `capture_result` no reemplaza el resultado original ni renderiza automáticamente.

## Configuración y valores predeterminados

No hay archivo de configuración dedicado. Registra la clase del handler mediante `app.withExceptionHandler(...)` antes de `create()`. La política HTTP base lee `app.debug`:

| Valor | Excepción HTTP desconocida |
|---|---|
| `False` | Estado 500 saneado con `Internal Server Error`. |
| `True` | Respuesta detallada con path y método del request. |

Las excepciones conocidas se mapean a 401 autenticación, 403 autorización, 404 ruta no encontrada, 405 método no permitido, 413 payload demasiado grande, 415 media type no soportado y 419 discrepancia CSRF. El mapeo HTTP recorre el MRO e incluye subclases. La negociación de contenido usa `request.wantsJson()`.

`dont_catch` es un `frozenset` de clases exactas definido en la clase. La coincidencia suprime logging y presentación predeterminados. Las subclases no se ignoran implícitamente. `context.expected=True` suprime logging ERROR predeterminado y conserva presentación. `context.reporting_allowed=False` suprime el uso predeterminado del logger durante el cierre final; los callbacks personalizados de logging deben respetarlo.

## Límites de fallos y ciclo de vida

- La ausencia de scope o `kernel` produce `RuntimeError` en `Catch.exception()`; usa captura para recepción sin scope.
- Pasa el request vivo o su adaptador para presentación HTTP. El plan base no produce salida HTTP sin él.
- El runtime protege la ejecución del hook y el logging diferido con comprobaciones de recursión, timeout cooperativo y fallback acotado en stderr. Un fallo del reporte puede degradar la entrega sin impedir la presentación.
- La cancelación, `KeyboardInterrupt`, `SystemExit` y `GeneratorExit` no se convierten en fallos de servidor.
- Antes de la activación, capturar retorna `None`. `create()` por sí solo no activa el runtime y los fallos anteriores al inicio exitoso quedan fuera de la garantía.
- El código externo que consume excepciones debe notificarlas explícitamente. Orionis no instala hooks globales de Python para ejecución externa arbitraria.
- El propietario de la ejecución debe declarar explícitamente un resultado fallido; el runtime no infiere fallo de cualquier valor retornado.

## Rendimiento y concurrencia

La aplicación reutiliza un handler preparado. El contexto de operación, la deduplicación y los planes aíslan el estado del incidente; las operaciones finalizadas liberan las referencias retenidas. Las operaciones y los intentos de reintento independientes no constituyen un único incidente global. Las dependencias del constructor y la política personalizada deben ser seguras durante la vida compartida del handler.

Los registros de incidentes y sus identificadores se asignan en los caminos de fallo. Los límites de ejecución y las tareas supervisadas aún realizan trabajo de contexto y ciclo de vida en ejecuciones exitosas; no se garantiza costo cero. El logging y la presentación diferidos evitan trabajo de protocolo cuando su propietario no lo solicita.

## Migrar un handler personalizado

Este cambio rompe compatibilidad. `report`, `handleHTTP` y `handleCLI` se eliminaron del contrato del handler y del handler base. Runtime y Catch no llaman los overrides antiguos y no hay wrappers de compatibilidad.

1. Mueve la política de excepciones a `handleFailure(exception, context)` y la de resultados fallidos a `handleResult(value, context)`.
2. Parte de `plan = await super().handleFailure(exception, context)` para conservar el comportamiento nativo. Retorna ese plan; esperarlo y descartar su retorno pierde los efectos diferidos.
3. Reemplaza logging o presentación asignando callbacks async al plan. Conserva el callback de presentación heredado cuando otros flujos lo necesiten. Usa `context.reporting_allowed` al añadir logging.
4. Mantén el estado de los callbacks local al incidente. Deja que el runtime complete logging y que el propietario del protocolo solicite presentación. No vuelvas a capturar desde ninguno de los hooks.

Las implementaciones directas de `IBaseExceptionHandler` deben implementar ambos métodos abstractos y pueden retornar `None` para recepción sin efectos. El `handleResult` base retorna `None`, por lo que los overrides que deleguen también deben retornar su resultado.

Orionis requiere Python 3.14+ y usa sus servicios HTTP, auth, logging, console y container sin añadir una dependencia externa separada para este módulo.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `catch.py` | Captura y despacho de presentación usando el plan del incidente. |
| `runtime.py` | Activación posinicio, finalización protegida, captura, supervisión y deduplicación. |
| `entities/context.py` | Contexto inmutable y recibo de entrega. |
| `entities/handling.py` | Logging diferido y presentación conservada para un incidente. |
| `base/handler.py` | Política predeterminada seleccionada por los dos hooks de aplicación. |
| `entities/throwable.py` | Registro estructurado de excepción con traceback nativo. |
| `enums/kernel_type.py` | Marcadores de scope `CONSOLE` y `HTTP`. |
| `contracts/` | Interfaces de Catch y del handler con dos hooks. |
| `provider.py` | Binding singleton y fijación de fachada. |

## Fuentes y siguientes pasos

[Contrato del handler](../../contracts/handler.py) · [Handler base](../../base/handler.py) · [Plan de manejo](../../entities/handling.py) · [Contexto](../../entities/context.py)

[Volver al índice del módulo](README.md).
