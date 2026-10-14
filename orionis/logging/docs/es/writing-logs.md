# Registrar eventos de aplicación

El logger registra eventos de aplicación en archivos UTF-8 con un canal activo y filtros de severidad.

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

## Incorporar logging a un servicio

Usa `from orionis.support.facades import Log` después de inicializar la aplicación, o recibe `ILogger` por inyección desde `orionis.logging.contracts.logger`. Sus métodos son síncronos y reciben un mensaje `str`: `info`, `warning`, `error`, `debug` y `critical`. No añadas `await` ni pases argumentos de interpolación como en el logger estándar.

Incluye un identificador de operación y un evento estable, por ejemplo `Log.info("invoice=42 event=sent")`. Conserva errores completos solo donde resulte necesario y filtra secretos antes de formar el mensaje. No se incluye redacción automática, contexto de request ni formateador JSON. Los saltos de línea aportados por usuarios pueden producir registros ambiguos; normaliza datos no confiables antes de interpolarlos.

Para registrar excepciones con traceback, obtén el logger estándar mediante `getLogger()` y usa sus APIs habituales, como `.exception(...)` dentro del bloque `except`. Eso utiliza el mismo archivo y los mismos handlers compartidos. El logger de Orionis desactiva propagación: los handlers del root logger no reciben automáticamente estos registros.

Cada wrapper utiliza el nombre global `__orionis__`. Inicializar dos wrappers aislados en el mismo proceso puede reemplazar los handlers del otro; en una aplicación utiliza el singleton del provider. Los ejemplos con dobles de aplicación son escenarios aislados, no una recomendación para crear un logger por solicitud.


### Logger y canal

`Logger` envuelve el logger estándar `__orionis__`, desactiva propagación y establece el logger en `DEBUG`; el handler activo aplica el umbral configurado. Un canal describe un handler y su política de ruta. Solo un canal está activo aunque haya varios configurados.

### Inicialización lazy

Construir `Logger` no toca el filesystem. El primer mensaje o `getLogger()` inicializa bajo lock con doble comprobación. Los formatters se comparten por clave de formatos. `close()` retira y cierra handlers y reinicia el wrapper para reconstruirlo después.

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

### Usar la facade de aplicación

```python
from orionis.support.facades import Log

Log.info("Request completed")
Log.warning("Retry budget is low")
Log.error("Job failed")
```

## Integración con Orionis

`LoggerProvider` enlaza `ILogger` a `Logger` como singleton con alias `x-orionis-ILogger` y fija `Log` al iniciar. El manejo de fallos inyecta `ILogger`; las tareas en segundo plano usan la facade. Otros módulos dependen del contrato sin conocer la rotación.

El nombre estándar se comparte en todo el proceso. Crear o inicializar otro `Logger` de Orionis cierra y reemplaza handlers de ese logger, por lo que la aplicación debe usar el singleton del provider.



### `Logger(app)`

- `info(message)`, `error(message)`, `warning(message)`, `debug(message)` y `critical(message)` reenvían strings al logger estándar.
- `getLogger()` devuelve el `logging.Logger` configurado para funciones avanzadas.
- `switchChannel(name)` reemplaza el handler y devuelve si tuvo éxito.
- `reloadConfiguration()` cierra handlers, relee `app.config("logging")`, reconstruye y registra un mensaje de éxito.
- `close()` libera archivos y permite reconstrucción lazy posterior.
- `getActiveChannels()` / `getActiveChannel()` informan el estado de handlers.
- `getAvailableChannels()` devuelve nombres configurados sin inicializar I/O.

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md) · [failure](../../../failure/docs/es/README.md)
