# orionis.metadata

> `orionis.metadata` expone la identidad, versión, compatibilidad y enlaces canónicos de la distribución Orionis.

## Descripción general

Este paquete es una superficie compuesta únicamente por constantes. Permite que el framework, comandos de consola, verificaciones de empaquetado y aplicaciones lean la misma identidad sin analizar `pyproject.toml` durante la ejecución.

La raíz del paquete reexporta todos los valores públicos de `orionis.metadata.framework`. Los valores son strings inmutables excepto `PYTHON_REQUIRES`, que es una tupla de enteros.

## Requisitos

- Python 3.14 o posterior, según declara `PYTHON_REQUIRES`.
- No se necesita iniciar la aplicación, contenedor, variables de entorno, acceso al sistema de archivos ni red para importar el paquete.

## Inicio rápido

```python
from orionis.metadata import NAME, PYTHON_REQUIRES, VERSION

assert NAME == "orionis"
assert PYTHON_REQUIRES == (3, 14)
major, minor, patch = (int(part) for part in VERSION.split("."))
print(NAME, (major, minor, patch))
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Conceptos principales

### Una superficie runtime canónica

`framework.py` posee diez constantes públicas. `orionis.metadata.__init__` las importa por referencia y enumera exactamente esos nombres en `__all__`. Los consumidores pueden importar desde el paquete, mientras herramientas que necesitan el namespace agrupado pueden importar `framework`.

### Metadatos de versión

`VERSION` es un string de versión numérica de tres segmentos. `NAME`, `DESCRIPTION`, `AUTHOR` y `AUTHOR_EMAIL` reflejan el manifiesto de distribución. Las pruebas del repositorio detectan divergencias entre estos valores y `pyproject.toml`.

### Metadatos de compatibilidad

`PYTHON_REQUIRES` guarda el intérprete mínimo como `(major, minor)`, lo cual permite compararlo directamente con `sys.version_info`. No es un string de requisito de empaquetado; el manifiesto deriva la forma equivalente `>=major.minor`.

### Ubicaciones del proyecto

`API`, `DOCS`, `FRAMEWORK` y `SKELETON` son URL HTTPS absolutas para datos JSON de PyPI, documentación y los dos repositorios. Las constantes describen ubicaciones; importar el módulo nunca contacta esos destinos.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `framework.py` | Define los diez valores canónicos e inmutables. |
| `__init__.py` | Reexporta esos valores y declara la API pública exacta. |
| `icon.svg` | Arte del paquete; la API Python no lo importa. |

## API pública

| Constante | Significado |
|---|---|
| `NAME` | Identidad de distribución/import, `orionis`. |
| `VERSION` | Versión actual de tres partes. |
| `DESCRIPTION` | Resumen de distribución en una línea. |
| `AUTHOR` / `AUTHOR_EMAIL` | Identidad y contacto del mantenedor. |
| `PYTHON_REQUIRES` | Tupla `(major, minor)` mínima de Python. |
| `API` | Endpoint JSON de PyPI. |
| `DOCS` | Raíz de documentación. |
| `FRAMEWORK` | Repositorio fuente principal. |
| `SKELETON` | Repositorio del esqueleto de aplicación. |

Los valores actuales exactos están versionados en `framework.py`. Trátelos como datos de release: léalos libremente, pero actualícelos solo como parte del cambio correspondiente de versión o metadatos.

## Flujos de trabajo comunes

### Mostrar información del framework

Importe constantes de nivel de paquete para construir una pantalla "acerca de", encabezado diagnóstico o componente de user-agent. No copie literales de versión en otros módulos.

### Aplicar el mínimo del intérprete

Compare los elementos iniciales de `sys.version_info` con `PYTHON_REQUIRES`. Las herramientas de empaquetado deben seguir usando `project.requires-python` de la distribución en vez de importar código durante la instalación.

### Enlazar recursos del proyecto

Use `DOCS`, `FRAMEWORK` o `SKELETON` cuando una salida del framework necesite enlaces estables. `API` identifica un endpoint, no garantiza que una solicitud de red tendrá éxito.

### Preparar una versión

Mantenga `VERSION`, nombre, descripción, autor, requisito de Python y URL sincronizados con `pyproject.toml`. La suite de metadata comprueba ese contrato.

## Ejemplos

### Inspeccionar todos los exports compatibles

```python
import orionis.metadata as metadata

values = {name: getattr(metadata, name) for name in metadata.__all__}
assert set(values) == {
    "API", "AUTHOR", "AUTHOR_EMAIL", "DESCRIPTION", "DOCS",
    "FRAMEWORK", "NAME", "PYTHON_REQUIRES", "SKELETON", "VERSION",
}
assert all(isinstance(value, (str, tuple)) for value in values.values())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Comprobar compatibilidad del intérprete

```python
import sys
from orionis.metadata import PYTHON_REQUIRES

running = sys.version_info[: len(PYTHON_REQUIRES)]
if running < PYTHON_REQUIRES:
    required = ".".join(map(str, PYTHON_REQUIRES))
    raise RuntimeError(f"Orionis requires Python {required}+")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Analizar la versión para compararla

```python
from orionis.metadata import VERSION

release = tuple(int(segment) for segment in VERSION.split("."))
assert len(release) == 3
assert release > (0, 0, 0)
print(release)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Construir el endpoint PyPI sin duplicarlo

```python
from urllib.parse import urlparse
from orionis.metadata import API, NAME

assert API == f"https://pypi.org/pypi/{NAME}/json"
assert urlparse(API).scheme == "https"
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; no se realizó ninguna solicitud de red.

## Configuración

El módulo no tiene configuración runtime ni lee variables de entorno. Sus valores son constantes Python mantenidas con la versión del proyecto. `pyproject.toml` es la declaración de empaquetado; las pruebas del repositorio comparan campos comunes, pero los imports de producción no analizan ese archivo.

## Integración con Orionis

La guarda de versión de la aplicación y los comandos informativos consumen estas constantes. El empaquetado y los reportes runtime comparten así la misma identidad y mínimo compatible. Importar `orionis.metadata` es seguro antes de que exista una `Application` y no toca el contenedor.

## Errores y casos límite

- `VERSION` es un string de versión simple, no un parser completo PEP 440 ni un rango.
- `PYTHON_REQUIRES` solo contiene major y minor; compare el mismo prefijo de `sys.version_info`.
- Las URL no se comprueban por accesibilidad al importar.
- Python permite reasignar atributos de módulo; los consumidores deben tratar los exports como solo lectura.
- Los wheels instalados pueden no contener `pyproject.toml`; el uso runtime no depende de su presencia.

## Rendimiento y concurrencia

El trabajo de importación se limita a enlazar strings, una tupla y reexports. No hay I/O, bloqueos, caché, colecciones mutables, trabajo async ni estado por solicitud. Las lecturas concurrentes son seguras bajo la semántica normal de módulos Python.

## Compatibilidad

`PYTHON_REQUIRES == (3, 14)` es el mínimo runtime autoritativo de este módulo y coincide con el manifiesto durante la verificación del repositorio. La API pública consta únicamente de los diez nombres de `__all__`; agregar o retirar una constante cambia API y tooling de release.

## Notas de verificación

- `tests/metadata`: **38 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Cinco programas bilingües de documentación se compilaron y ejecutaron correctamente.
- Las pruebas verifican exports exactos, forma inmutable, identificadores, URL, formatos de versión/contacto, compatibilidad Python y coincidencia con `pyproject.toml`.

