# Políticas de errores y referencia

## API pública

### `Catch(app)`

Único símbolo exportado por `orionis.failure`. Su método async `exception(exception, request=None)` resuelve/cachea handler, lee `kernel`, reporta y despacha. Construcción directa es principalmente infraestructura; aplicaciones usan la fachada o reciben `ICatch` por inyección.

### `BaseExceptionHandler`

- `toThrowable(exception)` convierte argumentos a string y conserva traceback nativo.
- `isExceptionIgnored(exception)` prueba membresía exacta en `dont_catch`.
- `report(exception, log)` registra `[ClassName] message` y retorna `Throwable`, o `None` si se ignora.
- `handleCLI(exception, console)` delega a `console.exception` salvo ignorados.
- `handleHTTP(exception, request)` construye respuesta mapeada, de producción o debug.

### `Throwable`

Dataclass congelada, keyword-only y slotted con `classtype`, `message`, `args` como strings y `traceback` nativo opcional. No se serializa ni formatea por sí sola.

### Contratos y fachada

`ICatch` se exporta desde `orionis.failure.contracts`; `IBaseExceptionHandler` está en su módulo definidor. La fachada es `orionis.support.facades.Catch`, distinta del export concreto.

## Configuración

No existe config dedicada. El handler lee `app.debug`:

| Valor | Excepción HTTP desconocida |
|---|---|
| `False` | Estado 500 saneado con `Internal Server Error`. |
| `True` | Respuesta detallada con path/método y excepción. |

La clase handler se registra mediante la API de aplicación. `dont_catch` es política en código, no ajuste de entorno.

## Errores y casos límite

- Scope activo o `kernel` ausente lanza `RuntimeError`; no se puede reportar con seguridad.
- Contexto HTTP sin request usable falla al pedir `wantsJson()`; pasa siempre request/adaptador.
- `isExceptionIgnored` exige instancia `BaseException` y rechaza otros objetos con `TypeError`.
- Ignorar compara exactamente `type(exception)`; el mapeo HTTP recorre MRO e incluye subclases.
- Si el reporte falla, no se ejecuta el renderer.
- `KeyboardInterrupt`, `SystemExit` y otros `BaseException` pueden llegar; decídelo explícitamente.

Estados mapeados: 401 autenticación, 403 autorización, 404 ruta, 405 método, 413 payload, 415 media type y 419 CSRF.

## Rendimiento y concurrencia

La primera llamada concurrente resuelve el handler detrás de `asyncio.Lock`; las siguientes lo reutilizan sin lock. Scope y kernel se consultan por excepción porque son locales al contexto. Conversión y mapeo son operaciones pequeñas; logging y render dominan el costo.

El singleton conserva solo el handler resuelto; request y excepción son locales a cada corrutina. Handlers personalizados deben mantener esa propiedad para concurrencia HTTP segura.

## Compatibilidad

Orionis declara Python 3.14+. El módulo depende de contratos Orionis HTTP, auth, logging, console y container, sin dependencia externa separada.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `catch.py` | Resolución del handler, reporte y despacho por kernel. |
| `base/handler.py` | Reporte, salida CLI, mapeo HTTP y política debug. |
| `entities/throwable.py` | Registro estructurado congelado y slotted. |
| `enums/kernel_type.py` | Marcadores `CONSOLE` y `HTTP`. |
| `contracts/` | Interfaces abstractas de catch y handler. |
| `provider.py` | Binding singleton y fijación de fachada. |

## Fuentes y siguientes pasos

[handler.py](../../base/handler.py) · [throwable.py](../../entities/throwable.py) · [handler.py](../../contracts/handler.py)

[Volver al índice del módulo](README.md).
