# Configurar rotación y ciclo de vida

El canal determina cuánto crecen los archivos y cómo se retienen. La configuración debe concordar con el número de workers y la política de operación.

## Operar archivos rotados

`stack` escribe en un solo archivo sin rotación; su nombre no significa una pila de canales. Los canales de tiempo rotan cuando llega un registro con un sufijo distinto: no existe un hilo que cree archivos en períodos sin tráfico. `daily.at` calcula la siguiente hora de rotación en el resolver, pero el handler decide por cambio de sufijo; no presupongas un scheduler que rote exactamente a la hora configurada.

El límite de tamaño se comprueba antes de escribir utilizando bytes ya registrados; una entrada puede llevar el archivo por encima del límite antes de la siguiente comprobación. La retención cuenta archivos que coinciden con el patrón, ordenados por mtime; no garantiza borrar datos exactamente al cumplir una edad. Incluye disco disponible y retención externa en tu operación.

`switchChannel()` quita handlers antes de crear el reemplazo. Un `False` después de un error no implica que el canal anterior siga activo. Comprueba `getActiveChannel()` y registra el fallo por un canal operativo disponible. `reloadConfiguration()` lee otra vez `app.config("logging")`: no vuelve a cargar automáticamente `.env` ni archivos Python. Cambiar el archivo en disco no es por sí solo un cambio de configuración de una aplicación ya iniciada.

### Extender la salida

`getLogger()` permite integrar handlers estándar. La siguiente recarga o cierre puede retirarlos: coordina su ownership. Para una política de rotación propia puedes construir `AdvancedRotatingFileHandler` con una implementación de `SuffixResolver` (`getSuffix`, `getNextRotationTime`); la factory integrada solo conoce los seis nombres documentados. No hay registro `extend()` de canales en `Logger`. Sustituye `ILogger` en tu provider si necesitas otra política global.

Los locks son de hilo, no de proceso. Varios workers sobre el mismo patrón pueden rotar o borrar archivos mutuamente. Usa rutas separadas por worker o una infraestructura externa de agregación. La emisión, compresión y limpieza son síncronas y pueden añadir latencia al loop.


### Rotación

Los canales de tiempo usan un resolver y rotan cuando cambia su sufijo. Hourly usa `YYYY-MM-DD_HH`, daily `YYYY-MM-DD`, weekly año/semana ISO y monthly `YYYY-MM`. `chunked` rota al alcanzar `mb_size` en bytes codificados, genera sufijos timestamp/contador y comprime rotados con gzip.

### Retención

Los handlers rotativos examinan solo archivos que coinciden con su template, los ordenan por modificación y eliminan los que exceden el backup count. La retención representa periodos del canal: horas, días, semanas, meses o cantidad de archivos; no una duración universal.

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

### Resolver sufijos de tiempo deterministas

```python
from datetime import UTC, datetime, time
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver

moment = datetime(2026, 10, 6, 15, 30, tzinfo=UTC)
assert DailySuffixResolver(time(2, 0)).getSuffix(moment) == "2026-10-06"
assert WeeklySuffixResolver().getSuffix(moment) == "2026-week41"
assert MonthlySuffixResolver().getSuffix(moment) == "2026-10"
print(DailySuffixResolver(time(2, 0)).getNextRotationTime(moment))
```

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



### Internos de rotación

`RotatingHandlerFactory.createHandler(channel_name, channel_config, app_root)` devuelve `FileHandler`, `AdvancedRotatingFileHandler` o `None` para canal no soportado. Cada `SuffixResolver` ofrece `getSuffix(dt=None)` y `getNextRotationTime(current_time)`.

## Referencia de implementación para extensiones

| Ruta | Responsabilidad |
|---|---|
| `logger.py` | Construcción lazy, niveles, cambio/recarga de canal y limpieza. |
| `provider.py` | Singleton del contenedor y fijación de `Log`. |
| `contracts/logger.py` | Contrato `ILogger`. |
| `contracts/suffix_resolver.py` | Contrato de sufijo/tiempo de rotación. |
| `handlers/rotating_handler_factory.py` | Despacho de canal a handler. |
| `handlers/advanced_rotating_file_handler.py` | Escritura segura, rotación, compresión y retención. |
| `handlers/*_suffix_resolver.py` | Políticas hourly, daily, weekly, monthly y chunked. |

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md)
