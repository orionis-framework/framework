# orionis.test

> `orionis.test` amplía `unittest` con inyección de dependencias Orionis, ejecución asíncrona, resultados estructurados, reportes Rich y pruebas MCP en proceso.

## Descripción general

`orionis.test` es la capa de pruebas asíncronas de Orionis sobre `unittest` de Python. Ofrece un `TestCase` consciente de la aplicación, un motor configurable de descubrimiento y ejecución, resultados estructurados, reportes Rich en consola y un cliente MCP en proceso que recorre la serialización JSON-RPC y el dispatcher reales.

El paquete está diseñado para pruebas del framework y de aplicaciones que necesitan inyección de dependencias de Orionis sin abandonar las aserciones, fixtures, omisiones, fallos esperados o subpruebas habituales de `unittest`.

## Requisitos

- Python 3.14 o posterior.
- Una estructura normal de aplicación Orionis cuando las pruebas requieran servicios de la aplicación.
- Módulos y métodos de prueba cuyos nombres coincidan con los patrones configurados.
- Una declaración de servidor MCP y un contenedor de aplicación arrancable para pruebas de integración MCP.

## Inicio rápido

```python
from orionis.test import TestCase

class TestArithmetic(TestCase):
    async def testAddition(self) -> None:
        self.assertEqual(2 + 2, 4)
```

Ejecuta la suite desde la raíz del proyecto:

```powershell
python reactor test
python reactor test --start-dir tests/unit --no-panel --verbosity 1
```

## Conceptos principales

### Casos conscientes de la aplicación

`TestCase` extiende `unittest.IsolatedAsyncioTestCase`. Al construirse envuelve solo el método seleccionado —no los hooks del ciclo de vida— y lo ejecuta mediante `Application.invoke()`. Así los métodos reciben la misma resolución automática de dependencias que los callables de la aplicación. La ruta de invocación acepta métodos de prueba síncronos y asíncronos.

Cada caso obtiene un event loop aislado. El umbral de callbacks lentos se establece en un segundo y se conserva el modo de depuración de asyncio. El patrón de nombres vive en un `ContextVar`, por lo que contextos concurrentes de descubrimiento no se sobrescriben.

### Descubrimiento y ejecución

`TestingEngine` recorre recursivamente el directorio configurado, incluidos directorios sin `__init__.py`, carga archivos coincidentes y filtra métodos individuales. Crea una suite nueva en cada ejecución y envía el runner síncrono de `unittest` a un executor para no bloquear el event loop del llamador.

### Resultados estructurados

`TestResultProcessor` convierte éxitos, fallos, errores, omisiones, fallos esperados, éxitos inesperados y resultados de subpruebas en entidades `TestResult`. Un resultado registra estado, duración, ubicación, documentación, detalles de excepción, traceback y código fuente cercano. La caché JSON opcional serializa estas entidades bajo `storage/framework/cache/testing`.

### Pruebas MCP a nivel de protocolo

`McpTestClient` compila un servidor una vez, envía mensajes JSON-RPC codificados mediante `McpDispatcher` y crea un ámbito nuevo del contenedor por petición o stream. `McpTestResponse` expone el mensaje final decodificado junto a las notificaciones recopiladas y aserciones breves de éxito y texto retornado.

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

## Flujos de trabajo comunes

### Probar dependencias resueltas

Anota el método como cualquier callable invocado por la aplicación. Orionis resuelve el parámetro cuando el runner invoca el caso:

```python
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.test import TestCase

class TestHealth(TestCase):
    async def testCache(self, cache: ICacheManager) -> None:
        await cache.put("health", "ok", seconds=10)
        self.assertEqual(await cache.get("health"), "ok")
```

### Comprobar una respuesta MCP

```python
from orionis.test import McpTestResponse

response = McpTestResponse({
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [{"type": "text", "text": "Hello, Ada"}],
        "isError": False,
    },
})
response.assertOk()
response.assertTextContains("Ada")
assert response.notifications == ()
```

### Inspeccionar un resultado estructurado

```python
from orionis.test.entities.result import TestResult
from orionis.test.enums.status import TestStatus

result = TestResult(
    id="case-1",
    name="tests.unit.TestUsers.testCreate",
    status=TestStatus.PASSED,
    execution_time=0.012,
)

payload = result.toDict()
assert payload["status"] == "PASSED"
assert payload["execution_time"] == 0.012
```

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

### Ejercitar una herramienta MCP real

```python
from orionis.mcp import Server, Tool
from orionis.test import TestCase

class GreetingServer(Server):
    tools = [Tool(name="hello", handler=lambda name: f"Hello, {name}")]

class TestGreetingServer(TestCase):
    async def testHello(self) -> None:
        client = await self.mcp(GreetingServer)
        response = await client.tool("hello", {"name": "Ada"})
        response.assertOk()
        response.assertTextContains("Hello, Ada")
```

## Configuración

La entidad de configuración `testing` lee estas variables de entorno:

| Variable de entorno | Predeterminado | Significado |
| --- | --- | --- |
| `TESTING_VERBOSITY` | `2` | `0` silencioso, `1` compacto, `2` detallado. |
| `TESTING_FAIL_FAST` | `False` | Detenerse tras el primer fallo o error. |
| `TESTING_START_DIR` | `tests` | Raíz de descubrimiento. |
| `TESTING_FILE_PATTERN` | `test_*.py` | Patrón de archivos. |
| `TESTING_METHOD_PATTERN` | `test*` | Patrón de métodos. |
| `TESTING_CACHE_RESULTS` | `False` | Persistir resultados estructurados como JSON. |

Los argumentos CLI sustituyen los valores configurados correspondientes. `--no-panel` oculta los paneles Rich inicial y final independientemente de la verbosidad por prueba.

## Integración con Orionis

`TestingProvider` enlaza `ITestingEngine` como singleton y fija la fachada `Test` durante el arranque. El comando `reactor test` resuelve ese motor, aplica las opciones de línea de comandos, lo ejecuta y deriva el estado del proceso a partir de los resultados estructurados.

`TestCase.mcp()` reutiliza por defecto la aplicación ya arrancada. Pasa `app=` solo cuando una prueba posea deliberadamente otro contenedor compatible. Esto evita que el cliente MCP cree silenciosamente una aplicación paralela con bindings distintos.

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

## Notas de verificación

Esta documentación se regeneró contra la implementación actual y se verificó con CPython 3.14.6. El descubrimiento bajo `tests/test` ejecutó 178 resultados: 177 aprobados y uno fallido. El fallo es `TestPublishGates.testPublicationRequiresEveryMandatoryGate` en la subprueba del gate exitoso porque su fixture aislado copia `PUBLISH.ps1`, pero no el script `DOCS.ps1` que ahora invoca `PUBLISH.ps1`; esa condición de prueba del repositorio está fuera de este alcance limitado a documentación. Los primeros seis ejemplos Python se ejecutaron correctamente; el ejemplo MCP con inyección de dependencias se validó sintácticamente porque requiere una aplicación arrancada.
