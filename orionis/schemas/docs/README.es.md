# orionis.schemas

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

El inicializador de orionis.schemas expone 1 símbolos públicos. Esta referencia usa __all__, las rutas de exportación y los archivos fuente actuales como evidencia.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| ../__init__.py | Define las exportaciones del paquete. |
| orionis.schemas/ | Implementaciones y subpaquetes de esas exportaciones. |

## Referencia de API

| Símbolo | Importación verificada | Fuente | Declaración | Comportamiento observado |
| --- | --- | --- | --- | --- |
| Schema | from orionis.schemas import Schema | [schema.py](../schema.py) | Schema | Define the base class for Orionis schema declarations. Notes ----- Inherit ``msgspec.Struct`` behavior and the ``SchemaMeta`` metaclass pipeline, which compiles validation metadata and stores Orionis custom metadata on the resulting class. |
| Schema.toDict | from orionis.schemas import Schema | [schema.py](../schema.py) | def toDict(self) -> dict[str, object] | Convert the schema instance into a dictionary. Returns ------- dict[str, object] Dictionary containing the schema fields and their values. |

## Ejemplos de uso

    from orionis.schemas import Schema

La ruta de importación coincide con la tabla de API. Estado de importación: executed successfully under Python 3.14.3.

## Características de diseño

El paquete utiliza una superficie pública explícita. Los símbolos privados no se incluyen; las declaraciones se enlazan al propietario concreto.

## Rendimiento y concurrencia

No se declara una garantía uniforme en el nivel del paquete. Inspeccione cada archivo enlazado para E/S, corutinas, cachés, bloqueos y estado compartido.

## Notas de compatibilidad

Mínimo declarado: Python 3.14. La validación usó Python 3.14.3. Los límites de dependencias están en pyproject.toml.

## Verificación y limitaciones

Se analizaron los archivos Python y se verificaron las exportaciones. Las excepciones de dependencias, callbacks, E/S o configuración pueden propagarse y no se presentan como exhaustivas.
