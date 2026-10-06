# orionis.logging

> `orionis.logging` proporciona el logger lazy por canales de Orionis, con rotación por tiempo y tamaño.

## Descripción general

La raíz exporta `Logger`, implementación de `ILogger` basada en el módulo estándar `logging`. Lee configuración validada, crea su primer handler solo al necesitarlo, escribe archivos UTF-8 y permite cambiar o recargar canales en runtime.

Orionis admite un archivo simple `stack` y rotación `hourly`, `daily`, `weekly`, `monthly` y `chunked` por tamaño. El provider enlaza el servicio como singleton y fija la facade `Log` para toda la aplicación.

## Requisitos

- Python 3.14 o posterior.
- Un directorio de logs escribible para los canales configurados.
- Un mapping de configuración `logging` válido, normalmente creado por `config/logging.py`.
- Una aplicación Orionis iniciada al usar `orionis.support.facades.Log`.

## Inicio rápido

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.logging import Logger


class App:
    def __init__(self, root: str) -> None:
        self.root = root

    def config(self, name: str) -> dict:
        assert name == "logging"
        return {
            "default": "stack",
            "channels": {"stack": {"path": "app.log", "level": "INFO"}},
        }

    def path(self, name: str) -> str:
        assert name == "root"
        return self.root


with TemporaryDirectory() as root:
    logger = Logger(App(root))
    logger.info("Orionis is ready")
    logger.close()
    assert "Orionis is ready" in (Path(root) / "app.log").read_text(encoding="utf-8")
    print(Logger.name)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; el directorio temporal se elimina automáticamente.

## Conceptos principales

### Logger y canal

`Logger` envuelve el logger estándar `__orionis__`, desactiva propagación y establece el logger en `DEBUG`; el handler activo aplica el umbral configurado. Un canal describe un handler y su política de ruta. Solo un canal está activo aunque haya varios configurados.

### Inicialización lazy

Construir `Logger` no toca el filesystem. El primer mensaje o `getLogger()` inicializa bajo lock con doble comprobación. Los formatters se comparten por clave de formatos. `close()` retira y cierra handlers y reinicia el wrapper para reconstruirlo después.

### Rotación

Los canales de tiempo usan un resolver y rotan cuando cambia su sufijo. Hourly usa `YYYY-MM-DD_HH`, daily `YYYY-MM-DD`, weekly año/semana ISO y monthly `YYYY-MM`. `chunked` rota al alcanzar `mb_size` en bytes codificados, genera sufijos timestamp/contador y comprime rotados con gzip.

### Retención

Los handlers rotativos examinan solo archivos que coinciden con su template, los ordenan por modificación y eliminan los que exceden el backup count. La retención representa periodos del canal: horas, días, semanas, meses o cantidad de archivos; no una duración universal.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `logger.py` | Construcción lazy, niveles, cambio/recarga de canal y limpieza. |
| `provider.py` | Singleton del contenedor y fijación de `Log`. |
| `contracts/logger.py` | Contrato `ILogger`. |
| `contracts/suffix_resolver.py` | Contrato de sufijo/tiempo de rotación. |
| `handlers/rotating_handler_factory.py` | Despacho de canal a handler. |
| `handlers/advanced_rotating_file_handler.py` | Escritura segura, rotación, compresión y retención. |
| `handlers/*_suffix_resolver.py` | Políticas hourly, daily, weekly, monthly y chunked. |

## API pública

La raíz exporta deliberadamente solo `Logger`. Infraestructura puede importar `ILogger`, handlers y resolvers desde sus subpaquetes.

### `Logger(app)`

- `info(message)`, `error(message)`, `warning(message)`, `debug(message)` y `critical(message)` reenvían strings al logger estándar.
- `getLogger()` devuelve el `logging.Logger` configurado para funciones avanzadas.
- `switchChannel(name)` reemplaza el handler y devuelve si tuvo éxito.
- `reloadConfiguration()` cierra handlers, relee `app.config("logging")`, reconstruye y registra un mensaje de éxito.
- `close()` libera archivos y permite reconstrucción lazy posterior.
- `getActiveChannels()` / `getActiveChannel()` informan el estado de handlers.
- `getAvailableChannels()` devuelve nombres configurados sin inicializar I/O.

### Internos de rotación

`RotatingHandlerFactory.createHandler(channel_name, channel_config, app_root)` devuelve `FileHandler`, `AdvancedRotatingFileHandler` o `None` para canal no soportado. Cada `SuffixResolver` ofrece `getSuffix(dt=None)` y `getNextRotationTime(current_time)`.

## Flujos de trabajo comunes

### Registrar mediante la facade

Use `Log.info`, `Log.warning` o la severidad correspondiente. No incluya contraseñas, tokens, headers de autorización, claves ni datos personales. Prefiera mensajes concisos con identificadores estables.

### Cambiar el canal configurado

Defina `LOG_CHANNEL` antes del bootstrap. `switchChannel()` en runtime es local al proceso y reemplaza el único handler activo. Compruebe su booleano; canales desconocidos o imposibles no se activan.

### Recargar configuración

Tras actualizar la fuente de configuración llame `reloadConfiguration()`. La operación usa lock, pero otros threads comparten el logger subyacente; coordine recargas administrativas en vez de hacerlas frecuentemente.

### Integrar funciones estándar

Llame `getLogger()` solo cuando las cinco ayudas no basten. Agregar handlers externos modifica un logger compartido; su ownership/limpieza corresponde al llamador y un close/reload posterior puede retirarlos.

## Ejemplos

### Inspeccionar canales sin abrir archivos

```python
from orionis.logging import Logger


class App:
    def config(self, name: str) -> dict:
        return {
            "default": "stack",
            "channels": {
                "stack": {"path": "storage/logs/stack.log", "level": "INFO"},
                "daily": {"path": "storage/logs/daily_{suffix}.log", "level": "WARNING"},
            },
        }


logger = Logger(App())
assert logger.getAvailableChannels() == ["stack", "daily"]
assert logger.getActiveChannel() is None
logger.close()
print("configuration inspected")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; no se creó handler ni archivo.

### Cambiar de canal en runtime

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.logging import Logger


class App:
    def __init__(self, root: str) -> None:
        self.root = root

    def config(self, name: str) -> dict:
        return {
            "default": "stack",
            "channels": {
                "stack": {"path": "stack.log", "level": "INFO"},
                "chunked": {"path": "chunk_{suffix}.log", "level": "INFO", "mb_size": 1, "files": 2},
            },
        }

    def path(self, name: str) -> str:
        return self.root


with TemporaryDirectory() as root:
    logger = Logger(App(root))
    assert logger.switchChannel("chunked")
    logger.warning("written to chunked channel")
    assert logger.getActiveChannel() == "chunked"
    logger.close()
    assert any(Path(root).glob("chunk_*.log"))
    print("channel switched")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; los logs temporales se eliminaron automáticamente.

### Resolver sufijos de tiempo deterministas

```python
from datetime import datetime, time
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver

moment = datetime(2026, 10, 6, 15, 30)
assert DailySuffixResolver(time(2, 0)).getSuffix(moment) == "2026-10-06"
assert WeeklySuffixResolver().getSuffix(moment) == "2026-week41"
assert MonthlySuffixResolver().getSuffix(moment) == "2026-10"
print(DailySuffixResolver(time(2, 0)).getNextRotationTime(moment))
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Crear un handler diferido

```python
import logging
from tempfile import TemporaryDirectory
from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory

with TemporaryDirectory() as root:
    handler = RotatingHandlerFactory.createHandler(
        "stack",
        {"path": "logs/example.log", "level": logging.WARNING},
        root,
    )
    assert handler is not None
    assert handler.level == logging.WARNING
    assert handler.stream is None
    handler.close()
    print(type(handler).__name__)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; el modo diferido no creó archivo.

### Usar la facade de aplicación

```python
from orionis.support.facades import Log

Log.info("Request completed")
Log.warning("Retry budget is low")
Log.error("Job failed")
```

Validación: **Solo importación** en CPython 3.14.6; las llamadas requieren una aplicación iniciada y la facade fijada.

## Configuración

`config/logging.py` construye entidades inmutables para cada canal:

| Ajuste | Entorno | Predeterminado |
|---|---|---|
| Canal predeterminado | `LOG_CHANNEL` | `stack` |
| Nivel del handler | `LOG_LEVEL` | `INFO` |
| Ruta del canal elegido | `LOG_PATH` | Ruta del canal bajo `storage/logs/` |
| Retención del canal de tiempo elegido | `LOG_RETENTION` | hourly 24, daily 7, weekly 4, monthly 4 |
| Hora de rotación daily | `LOG_ROTATION_TIME` | `00:00:00` |
| Tamaño chunk | `LOG_MB_SIZE` | 10 MiB |
| Retención chunk | `LOG_FILES` | 5 archivos |

`LOG_PATH` y `LOG_RETENTION` sobrescriben solo el canal de `LOG_CHANNEL`; edite `config/logging.py` o use claves dedicadas para overrides independientes. Las rutas parten de la raíz. Los templates rotativos deberían contener `{suffix}` para separar periodos.

## Integración con Orionis

`LoggerProvider` enlaza `ILogger` a `Logger` como singleton con alias `x-orionis-ILogger` y fija `Log` al iniciar. El manejo de fallos inyecta `ILogger`; las tareas en segundo plano usan la facade. Otros módulos dependen del contrato sin conocer la rotación.

El nombre estándar se comparte en todo el proceso. Crear o inicializar otro `Logger` de Orionis cierra y reemplaza handlers de ese logger, por lo que la aplicación debe usar el singleton del provider.

## Errores y casos límite

- Fallos de inicialización y recarga se envuelven en `RuntimeError`.
- Un default ausente crea `storage/logs/default.log`; un canal presente pero no soportado puede dejar el logger sin handlers.
- `switchChannel()` devuelve `False` para canales ausentes, no soportados o fallidos y suprime errores comunes.
- Niveles string se normalizan con nombres estándar; desconocidos se vuelven `INFO`.
- Errores I/O de rotación/compresión/retención se manejan defensivamente; logging estándar puede reportar errores de handler.
- Retención `0` elimina rotados coincidentes. Templates sin `{suffix}` impiden archivos separados.
- `close()` es idempotente y suprime errores comunes; usar el wrapper después lo reconstruye.
- Procesos múltiples escriben independientemente y no coordinan locks de rotación.

## Rendimiento y concurrencia

El hot path usa filtrado estándar y un handler. Inicialización, recarga, cambio, emisión y sufijos chunk usan locks. Los handlers cachean aproximadamente 50 rutas durante cinco minutos y rastrean bytes escritos sin `stat` por registro.

Los locks son de thread, no de proceso. Evite workers apuntando al mismo archivo rotativo sin coordinación externa. Las escrituras son síncronas y pueden afectar al event loop con alto volumen; use cola/agregación a nivel de aplicación cuando el throughput sea considerable.

## Compatibilidad

Orionis declara Python 3.14+ y depende de `logging`, `pathlib`, `gzip` y zonas horarias estándar. Los archivos usan UTF-8 y los handlers avanzados LF explícito. `pathlib` soporta Windows/POSIX. Las fechas de sufijo usan la zona expuesta por la facade `DateTime`.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron export, `ILogger`, ciclo de vida, cachés, factories/resolvers, rotación/compresión/retención, entidades, provider/facade y consumidores. Los **178** métodos de prueba pasaron con el runner de Orionis. Cinco programas directos se ejecutaron correctamente; el ejemplo de facade se validó solo por importación.
