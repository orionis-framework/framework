# orionis.metadata

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

El inicializador de orionis.metadata expone 10 símbolos públicos. Esta referencia usa __all__, las rutas de exportación y los archivos fuente actuales como evidencia.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| ../__init__.py | Define las exportaciones del paquete. |
| orionis.metadata/ | Implementaciones y subpaquetes de esas exportaciones. |

## Referencia de API

| Símbolo | Importación verificada | Fuente | Declaración | Comportamiento observado |
| --- | --- | --- | --- | --- |
| API | from orionis.metadata import API | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| AUTHOR | from orionis.metadata import AUTHOR | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| AUTHOR_EMAIL | from orionis.metadata import AUTHOR_EMAIL | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| DESCRIPTION | from orionis.metadata import DESCRIPTION | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| DOCS | from orionis.metadata import DOCS | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| FRAMEWORK | from orionis.metadata import FRAMEWORK | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| NAME | from orionis.metadata import NAME | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| PYTHON_REQUIRES | from orionis.metadata import PYTHON_REQUIRES | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| SKELETON | from orionis.metadata import SKELETON | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| VERSION | from orionis.metadata import VERSION | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |

## Ejemplos de uso

    from orionis.metadata import API

La ruta de importación coincide con la tabla de API. Estado de importación: executed successfully under Python 3.14.3.

## Características de diseño

El paquete utiliza una superficie pública explícita. Los símbolos privados no se incluyen; las declaraciones se enlazan al propietario concreto.

## Rendimiento y concurrencia

No se declara una garantía uniforme en el nivel del paquete. Inspeccione cada archivo enlazado para E/S, corutinas, cachés, bloqueos y estado compartido.

## Notas de compatibilidad

Mínimo declarado: Python 3.14. La validación usó Python 3.14.3. Los límites de dependencias están en pyproject.toml.

## Verificación y limitaciones

Se analizaron los archivos Python y se verificaron las exportaciones. Las excepciones de dependencias, callbacks, E/S o configuración pueden propagarse y no se presentan como exhaustivas.
