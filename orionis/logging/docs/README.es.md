# orionis.logging

> Referencia de API derivada de la implementación actual.

## Tabla de contenido

- Requisitos
- Resumen funcional
- Estructura del módulo
- Referencia de API
- Ejemplos de uso
- Características de diseño
- Rendimiento y concurrencia
- Notas de compatibilidad
- Verificación y limitaciones

## Requisitos

Python 3.14 o superior, como declara pyproject.toml.

## Resumen funcional

El inicializador de orionis.logging expone 1 símbolos públicos. Esta referencia usa __all__, las rutas de exportación y los archivos fuente actuales como evidencia.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| ../__init__.py | Define las exportaciones del paquete. |
| orionis.logging/ | Implementaciones y subpaquetes de esas exportaciones. |

## Referencia de API

| Símbolo | Importación verificada | Fuente | Declaración | Comportamiento observado |
| --- | --- | --- | --- | --- |
| Logger | from orionis.logging import Logger | [logger.py](../logger.py) | Logger | Exported public constant or alias. |
| Logger.info | from orionis.logging import Logger | [logger.py](../logger.py) | def info(self, message: str) -> None | Log an informational message. Parameters ---------- message : str The message to log. Returns ------- None This method does not return a value. |
| Logger.error | from orionis.logging import Logger | [logger.py](../logger.py) | def error(self, message: str) -> None | Log an error message. Parameters ---------- message : str Error message to log. Returns ------- None This method does not return a value. |
| Logger.warning | from orionis.logging import Logger | [logger.py](../logger.py) | def warning(self, message: str) -> None | Log a warning message. Parameters ---------- message : str Warning message to log. Returns ------- None This method does not return a value. |
| Logger.debug | from orionis.logging import Logger | [logger.py](../logger.py) | def debug(self, message: str) -> None | Log a debug message. Parameters ---------- message : str Debug message to log. Returns ------- None This method does not return a value. |
| Logger.critical | from orionis.logging import Logger | [logger.py](../logger.py) | def critical(self, message: str) -> None | Log a critical message. Parameters ---------- message : str Critical message to log. Returns ------- None This method does not return a value. |
| Logger.getLogger | from orionis.logging import Logger | [logger.py](../logger.py) | def getLogger(self) -> logging.Logger | Return the internal logger instance for advanced usage. Returns ------- logging.Logger The configured logger instance. Raises ------ RuntimeError If the logger is not available. |
| Logger.reloadConfiguration | from orionis.logging import Logger | [logger.py](../logger.py) | def reloadConfiguration(self) -> None | Reload the logger configuration from the application. This method allows dynamic reloading of logger settings without restarting the application. Returns ------- None This method does not return a value. |
| Logger.switchChannel | from orionis.logging import Logger | [logger.py](../logger.py) | def switchChannel(self, channel_name: str) -> bool | Switch to a different logging channel. Initialize the logger when needed, close current handlers, clear caches, and create a new handler for the specified channel. Only one channel is active at a time. Parameters ---------- channel_name : str Name of the channel to switch to. Returns ------- bool True if the switch was successful, False otherwise. |
| Logger.close | from orionis.logging import Logger | [logger.py](../logger.py) | def close(self) -> None | Close all handlers and release logger resources. This method should be called when the logger is no longer needed to ensure that all file handles and resources are properly released. Returns ------- None This method does not return a value. |
| Logger.getActiveChannels | from orionis.logging import Logger | [logger.py](../logger.py) | def getActiveChannels(self) -> list[str] | Return the names of active logging channels. Returns ------- list[str] List containing the names of active logging channels. |
| Logger.getActiveChannel | from orionis.logging import Logger | [logger.py](../logger.py) | def getActiveChannel(self) -> str / None | Return the name of the currently active logging channel. Returns ------- str / None The name of the active channel, or None if no channel is active. |
| Logger.getAvailableChannels | from orionis.logging import Logger | [logger.py](../logger.py) | def getAvailableChannels(self) -> list[str] | Return all available logging channels from configuration. Returns ------- list[str] List of all configured channel names. |

## Ejemplos de uso

    from orionis.logging import Logger

La ruta de importación coincide con la tabla de API. Estado de importación: executed successfully under Python 3.14.3.

## Características de diseño

El paquete utiliza una superficie pública explícita. Los símbolos privados no se incluyen; las declaraciones se enlazan al propietario concreto.

## Rendimiento y concurrencia

No se declara una garantía uniforme en el nivel del paquete. Inspeccione cada archivo enlazado para E/S, corutinas, cachés, bloqueos y estado compartido.

## Notas de compatibilidad

Mínimo declarado: Python 3.14. La validación usó Python 3.14.3. Los límites de dependencias están en pyproject.toml.

## Verificación y limitaciones

Se analizaron los archivos Python y se verificaron las exportaciones. Las excepciones de dependencias, callbacks, E/S o configuración pueden propagarse y no se presentan como exhaustivas.
