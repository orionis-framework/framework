# Resultados, configuración y referencia

## API pública

Las importaciones estables desde la raíz son:

- `TestCase`: clase base para pruebas de aplicaciones Orionis.
- `McpTestClient`: cliente de peticiones, streams y llamadas a herramientas MCP.
- `McpTestResponse`: respuesta decodificada con `assertOk()` y `assertTextContains()`.

Las integraciones del framework también exponen:

- `TestingEngine`: setters fluidos `setVerbosity`, `setFailFast`, `setStartDir`, `setFilePattern`, `setMethodPattern`, `withoutPanel`; además de `discover()` y `run()` asíncrono.
- Fachada `Test`: proxy del contenedor que implementa el contrato del motor.
- `TestResult`: entidad inmutable con `toDict()` heredado de `BaseEntity`.
- `TestStatus`: enum de cadenas con los cuatro estados exportados.
- `TestRunner` y `TestResultProcessor`: puntos de integración de menor nivel con `unittest`.

## Errores y casos límite

- Ejecutar un caso consciente de la aplicación sin arrancarla hace fallar la resolución de dependencias.
- Los métodos de ciclo de vida (`setUp`, `tearDown` y variantes de clase/asíncronas) nunca se envuelven como métodos de prueba.
- Los fallos de importación encontrados por el loader se conservan en la suite en vez de ser eliminados por el filtro de métodos.
- `McpTestResponse.assertOk()` falla ante errores JSON-RPC y resultados de herramientas con `isError=True`.
- `request()` sirve para intercambios MCP finitos; usa `stream()` con suscripciones o respuestas abiertas.
- Los éxitos inesperados son fallos, mientras los fallos esperados se exportan como omitidos.
- Una subprueba fallida se representa en los resultados exportados y respeta fail-fast.
- Los nombres de la caché JSON usan timestamps con resolución de segundos; varias ejecuciones en el mismo segundo apuntan a la misma ruta.
- La salida con emojis de Rich requiere una terminal Unicode; en páginas de códigos antiguas de Windows configura `PYTHONUTF8=1`.

## Rendimiento y concurrencia

El descubrimiento crea un `TestLoader` y una suite nuevos en cada ocasión. La ejecución se mueve al executor de hilos predeterminado y cada `TestCase` posee su event loop. Los patrones de métodos son locales al contexto y el estado del procesador de resultados es local a su instancia, lo que permite ejecuciones independientes sin listas ni verbosidad compartidas.

Las peticiones MCP crean ámbitos independientes de la aplicación y cierran los cuerpos de stream en `finally`. El servidor MCP compilado y el bus de eventos en memoria se conservan en el cliente: reutiliza un cliente para probar varias operaciones del mismo servidor manteniendo cada petición dentro de su ámbito.

## Compatibilidad

El módulo requiere Python 3.14+ y extiende los protocolos estándar de `unittest`. Las aserciones y decoradores existentes de `unittest` siguen disponibles. Los filtros de métodos y archivos de Orionis usan semántica glob mediante `fnmatch`, no expresiones regulares. Rich solo controla la presentación; los objetos `TestResult` siguen siendo el contrato legible por máquinas.

## Estructura del módulo

| Ruta | Responsabilidad |
| --- | --- |
| `cases/case.py` | `TestCase` asíncrono aislado y consciente de la aplicación. |
| `clients/mcp.py` | Cliente MCP en proceso y aserciones de respuesta. |
| `contracts/engine.py` | Interfaz del motor usada por el contenedor. |
| `core/engine.py` | Configuración, descubrimiento recursivo, ejecución y caché JSON. |
| `entities/result.py` | `TestResult` estructurado e inmutable. |
| `enums/status.py` | Estados `PASSED`, `FAILED`, `ERRORED` y `SKIPPED`. |
| `executors/results.py` | Adaptador de `unittest.TestResult` y renderizado Rich. |
| `executors/runner.py` | Runner, panel inicial y panel resumen. |
| `provider.py` | Registro diferido del servicio y fijación de la fachada `Test`. |

## Ejemplos

### Usar el runner de menor nivel

```python
import unittest

from orionis.test.executors.runner import TestRunner

class PlainCase(unittest.TestCase):
    def testValue(self) -> None:
        self.assertTrue(True)

suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlainCase)
result = TestRunner(verbosity=0, with_panel=False).run(suite)
assert result.wasSuccessful()
assert result.testsRun == 1
```

### Validar la configuración de pruebas

```python
from orionis.foundation.config.testing import Testing, VerbosityMode

config = Testing(
    verbosity=VerbosityMode.MINIMAL,
    fail_fast=True,
    start_dir="tests/unit",
    file_pattern="test_*.py",
    method_pattern="testCreate*",
    cache_results=False,
)

assert config.verbosity == 1
assert config.fail_fast is True
```

## Fuentes y siguientes pasos

[result.py](../../entities/result.py) · [runner.py](../../executors/runner.py) · [results.py](../../executors/results.py)

[Volver al índice del módulo](README.md).
