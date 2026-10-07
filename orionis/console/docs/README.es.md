# orionis.console

> `orionis.console` impulsa la CLI `reactor` de Orionis, comandos personalizados, interacción de terminal, generadores de código y programación persistente de comandos.

## Descripción general

El módulo convierte clases de comando y registros fluidos en un registro gobernado por `argparse`. `KernelCLI` normaliza argumentos del proceso, `Reactor` descubre y ejecuta comandos dentro de un scope nuevo del contenedor, y `Console` proporciona salida con estilos y prompts. El mismo registro alimenta un servicio `Schedule` basado en APScheduler.

Autores de aplicaciones usan principalmente `BaseCommand`, `Argument`, `Console`, la fachada `Reactor` para registro fluido/llamadas programáticas y `Schedule` para comandos recurrentes. Orionis incluye comandos de servidor, pruebas, migraciones/inspección DB, colas, scheduler, rutas, mantenimiento de caché/logs/vistas, generadores, MCP y configuración de aplicación.

## Requisitos

- Python 3.14 o posterior.
- Dependencias declaradas `rich>=15,<16`, `apscheduler>=3.11.3,<4.0` y `psutil>=7.2.2,<8.0`.
- Una terminal para prompts interactivos y salida dinámica; comandos no interactivos pueden llamarse programáticamente.
- Redis o base de datos solo al seleccionar ese store del scheduler o un comando que necesite el servicio.
- Ejecuta comandos del proyecto mediante `reactor` para iniciar aplicación y providers.

## Inicio rápido

Define una clase comando con argumentos validados:

```python
from orionis.console import Argument
from orionis.console.base import BaseCommand


class GreetCommand(BaseCommand):
    signature = "greet"
    description = "Print a greeting."
    arguments = [
        Argument(name_or_flags="name", help="Name to greet."),
    ]

    async def handle(self) -> int:
        self.writeLine(f"Hello, {self.getArgument('name')}!")
        return 0
```

Registra `GreetCommand` como comando de la aplicación y ejecuta `python reactor greet Orionis`. El reactor analiza `name`, construye el comando por inyección, llama `handle` y devuelve su código entero.

Validación: **Import-validated only** en CPython 3.14.6; ejecutar la CLI requiere registro e inicio de la aplicación.

## Conceptos principales

### Definición, descubrimiento y ejecución

`BaseCommand` define metadatos y `handle`. `Loader` valida comandos core, de aplicación y fluidos, creando entidades inmutables con parsers. `Reactor.call` abre un scope de consola, analiza argumentos, construye el handler mediante el contenedor, mide, registra el resultado y convierte retornos no enteros en código `0`.

### Argumentos declarados

`Argument` es una descripción congelada y validada de un argumento `argparse`. Normaliza nombres a tupla y reenvía campos soportados a `add_argument`. Orionis reserva `-h`/`--help`; argumentos posicionales ignoran `required` porque argparse ya los exige salvo que `nargs` lo cambie.

### Comandos frente a tareas programadas

Un comando describe trabajo invocable ahora. `Schedule.command(signature, args, purpose)` crea una tarea fluida que referencia un comando existente y añade un trigger APScheduler. El scheduler persiste definiciones en memoria, Redis o database e invoca comandos mediante `Reactor`.

### Superficies de salida

`Console` proporciona estados con estilo, tablas, prompts, excepciones, dumps, barras y sleep async. `Dumper` formatea valores; `ProgressBar` es una barra ligera. `BaseCommand` hereda `Console`, así que usa sus métodos directamente.

## Estructura del módulo

| Área | Responsabilidad |
|---|---|
| `base/`, `args/`, `entities/` | Bases, argumentos y metadatos normalizados. |
| `core/`, `kernel.py`, providers | Descubrimiento, validación, despacho DI, rutas CLI y fachadas. |
| `output/`, `debug/`, `dynamic/` | Salida, prompts, ayuda, estado, dumps y progreso. |
| `fluent/` | Builders de comandos y tareas. |
| `tasks/`, `scheduler_provider.py` | Ciclo APScheduler, stores, listeners y ejecución. |
| `commands/` | Comandos incorporados de serve, test, make, DB, queue, MCP, schedule, route y support. |
| `templates/` | Carga/render de stubs para make. |

## API pública

### `BaseCommand`

Importa desde `orionis.console.base`. Las subclases declaran `signature`, `description`, `arguments` opcionales y `handle` async. `timestamps` vale `True`. `setArguments` combina un diccionario; `getArgument` conserva un `None` explícito; `getArguments()` devuelve copia superficial.

Dependencias del constructor y parámetros de `handle` pueden resolverse por el contenedor. Devuelve entero para controlar exit code; otros retornos exitosos se convierten en `0`.

### `Argument`

Campos principales: `name_or_flags`, `action`, `nargs`, `const`, `default`, `type_`, `choices`, `required`, `help`, `metavar`, `dest`, `version`, `extra`. `action` acepta string o `ArgumentAction`. Se rechaza `type_` con acciones booleanas/const, `choices` string y `action="version"` sin `version`.

### Fachada `Reactor`

Importa desde `orionis.support.facades.reactor` tras bootstrap:

| Método | Finalidad |
|---|---|
| `command(signature, handler)` | Registra comando fluido y devuelve builder. |
| `hasCommand(signature)` | Comprueba el registro async. |
| `info()` | Metadatos públicos ordenados, almacenados tras construirlos. |
| `call(signature, args=None)` | Ejecuta en scope nuevo y devuelve exit code. |

El builder configura `timestamp`, `description` y `arguments`. Registra antes de que se almacenen metadatos o termine boot.

### `Console`, `Dumper` y `ProgressBar`

La API `Console` se agrupa así:

- Estado: `success`, `info`, `warning`, `fail`, `error` con timestamp opcional.
- Estilos inline: familias `textSuccess`, `textInfo`, `textWarning`, `textError`, muted/bold/underline.
- Layout: `write`, `writeLine`, `line`, `newLine`, `clear`, `clearLine`, `table`.
- Entrada: `ask`, `confirm`, `secret`, `anticipate`, `choice`.
- Diagnóstico/control: `exception`, `dump`, `progressBar`, `sleep`, `exitSuccess`, `exitError`.

`Dumper.dump` imprime y devuelve valores; `dd` imprime y termina. `ProgressBar(total=100, width=50)` expone `start`, `advance`, `finish` con validación.

### Fachada `Schedule` y `Task`

Importa `Schedule` desde `orionis.support.facades.schedule`. Añade tareas solo detenido:

```python
Schedule.command("reports:daily", ["--format", "csv"], "Daily report").dailyAt(2, 30)
```

Builders cubren fechas únicas, intervalos, weekdays, cron, fechas inicio/fin, jitter, coalescing, gracia, instancias, purpose, store y listeners. Operaciones: `boot`, `info`, `state`, pausa/reanudación/eliminación de tareas, pausa/reanudación global, `shutdown`, `wait`.

### API de extensión

`BaseScheduler` aporta hooks y `BaseTaskListener` callbacks. Contratos cubren kernel, schedule/store, reactor/loader, command, output, progress y builders. Handlers personalizados siguen siendo clases construibles por contenedor.

## Flujos de trabajo comunes

### Crear y ejecutar comando

Hereda `BaseCommand`, declara `Argument`, registra la clase en comandos de aplicación e invócala mediante `reactor`. Lee valores con `getArgument`; solicita servicios por constructor o inyección en `handle`.

### Registrar comando fluido

Llama `Reactor.command("signature", [Handler, "method"])` y configura descripción, argumentos y timestamps. El mismo loader normaliza registros fluidos y clases.

### Llamar un comando desde código

Usa `await Reactor.call("signature", ["--flag", "value"])`. Cada llamada recibe scope con `KernelContext.CONSOLE`. Fallos se registran, envían al catcher y devuelven `1`.

### Instalar funciones opcionales del framework

`orionis packages` muestra funciones opcionales y herramientas de desarrollo por su propósito, y acepta nombres o números del catálogo. `--list` solo muestra el catálogo; `--yes` confirma la instalación seleccionada sin preguntar. El nombre público del comando es `packages`, no `install`.

```shell
orionis packages --list
orionis packages s3 redshift --yes
orionis packages group:dev --yes
```

El comando lee primero el manifiesto del framework incluido en `orionis/pyproject.toml`. Las instalaciones desde código fuente o editables usan el manifiesto de la raíz del framework cuando no existe una copia incluida en el paquete. Solo si ninguno de esos manifiestos está disponible recurre al de la raíz de la aplicación. La compilación incluye automáticamente el manifiesto canónico; no hay que mantener una segunda copia fuente.

Los propósitos de las opciones se definen en `[tool.orionis.packages]` del manifiesto seleccionado, con claves que incluyen su namespace:

```toml
[tool.orionis.packages]
"extra:s3" = "Amazon S3 file storage."
"group:dev" = "Development and quality checks."
```

La instalación utiliza `uv` con el intérprete que ejecuta Orionis. No reescribe el manifiesto ni el lockfile de la aplicación. Se conservan los extras, marcadores de entorno, inclusiones de grupos y eliminación de dependencias duplicadas.

### Programar un comando

Durante configuración llama `Schedule.command(...)` y completa el trigger. Ejecuta `python reactor schedule:work`; el scheduler carga comandos/store/jobs/listeners, maneja señales y espera cierre.

## Ejemplos

### Validar y analizar un `Argument`

```python
import argparse

from orionis.console import Argument


parser = argparse.ArgumentParser(add_help=False)
argument = Argument(
    name_or_flags=("-n", "--name"),
    required=True,
    type_=str,
    dest="name",
)
argument.addToParser(parser)
print(vars(parser.parse_args(["--name", "Orionis"])))  # {'name': 'Orionis'}
```

Validación: **Executed successfully** en CPython 3.14.6.

### Ejercitar almacenamiento de argumentos

```python
from orionis.console.base import BaseCommand


class CountCommand(BaseCommand):
    signature = "count"
    description = "Read a count."

    async def handle(self) -> int:
        return int(self.getArgument("count", 0))


command = CountCommand()
command.setArguments({"count": 3})
print(command.getArgument("count"))  # 3
print(command.getArguments())         # {'count': 3}
```

El diccionario devuelto es copia; cambiarlo no muta los argumentos guardados.

Validación: **Executed successfully** en CPython 3.14.6.

### Registrar un comando fluido

```python
from orionis.console import Argument
from orionis.support.facades.reactor import Reactor


class ReportHandler:
    async def run(self, format_name: str) -> int:
        return 0


def register_commands() -> None:
    Reactor.command("reports:build", [ReportHandler, "run"]).description(
        "Build a report."
    ).arguments([
        Argument(name_or_flags="--format", dest="format_name", default="json"),
    ])
```

Validación: **Import-validated only** en CPython 3.14.6; requiere fachada reactor iniciada/fijada.

### Definir un comando programado

```python
from orionis.support.facades.schedule import Schedule


def register_schedule() -> None:
    Schedule.command(
        "queue:clear",
        purpose="Remove completed queue records nightly.",
    ).coalesce().misfireGraceTime(60).dailyAt(3, 15)
```

Configura opciones encadenables antes del método terminal de trigger (`dailyAt` devuelve `True`). Debe registrarse antes de iniciar el scheduler; timezone procede de configuración de aplicación.

Validación: **Import-validated only** en CPython 3.14.6; ejecución persistente requiere bootstrap y store.

## Configuración

La CLI no tiene sección propia. Scheduling usa:

| Clave | Variable | Predeterminado |
|---|---|---|
| `scheduler.store` | `TASKS_STORE` | `memory` |
| `scheduler.max_instances` | `TASKS_MAX_INSTANCES` | `1` |
| `scheduler.coalesce` | `TASKS_COALESCE` | `True` |
| `scheduler.misfire_grace_time` | `TASKS_MISFIRE_GRACE_TIME` | `30` s |
| `scheduler.replace_existing` | `TASKS_REPLACE_EXISTING` | `True` |
| `scheduler.jitter` | `TASKS_JITTER` | `0` |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_TASKS_KEY`, `REDIS_RUN_TIMES_KEY` | Redis local y claves `scheduler:*` |
| Database | `DB_TASK_CONNECTION`, `DB_TASK_TABLE` | conexión predeterminada, `scheduler_tasks` |

Timezone es `app.timezone` (`APP_TIMEZONE`, `UTC`). Stores persistentes requieren `replace_existing=True` para reinicios idempotentes.

## Integración con Orionis

El script `reactor` entra en `protocol_stdio`, inicia aplicación y conduce `app.handleCommand` con `Loop.run`. Providers vinculan/fijan fachadas. Loader combina comandos incorporados, clases de aplicación y registros fluidos. Reactor usa contenedor, failure handler, logger y contador.

Comandos integran HTTP, tests, DB/ORM, queues, MCP, rutas, caché/vistas/logs, templates, entorno/encryption e instalación. Stores scheduler integran APScheduler, Redis o conexiones Orionis.

## Errores y casos límite

- Combinaciones inválidas de `Argument` fallan al construir; errores/help argparse producen `SystemExit` manejado por el flujo.
- Metadatos duplicados/mal formados se rechazan. Firmas desconocidas hacen que `Reactor.call` devuelva `1` mediante catch.
- Excepciones de comando se registran/delegan a `ICatch`; la ruta normal devuelve `1`.
- Programar tras inicio lanza `RuntimeError`; intervalos, horas, cron, listeners y estados inválidos lanzan errores de validación.
- Prompts pueden bloquear si stdin no está disponible.
- `exitSuccess` y `exitError` terminan mediante `SystemExit`.
- La suite agregada puede dejar casos prolongados de procesos/workers; diagnostícalos por grupos.

## Rendimiento y concurrencia

Metadatos y `Reactor.info()` se almacenan tras cargar. Cada llamada obtiene scope distinto; reactor y scheduler son singletons. Operaciones bloqueantes se mueven a executors donde la implementación lo declara.

APScheduler controla instancias, coalescing, misfires y jitter. Corrutinas listener se rastrean como tareas y drenan al cerrar. Memory es local al proceso; Redis/database persisten entre reinicios según semántica APScheduler.

Salida de consola es I/O síncrona. `Console.sleep` es async, pero prompts/impresión bloquean el hilo durante su I/O.

## Compatibilidad

Orionis declara Python 3.14+, Rich 15.x y APScheduler 3.11.x; se validó con CPython 3.14.6 en Windows. El protocolo adapta stdout binario en Windows. Serve selecciona comportamiento Granian apropiado. Redis/database dependen de drivers/servicios.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, bases, loader/reactor/kernel, salida, APIs fluidas, scheduler/stores, providers, registro de comandos, configuración y tests. Ejemplos se ejecutaron o validaron por import según se indica. La agregación completa de `tests/console` no se declara aprobada: quedó bloqueada en casos orientados a procesos tras varios minutos y se interrumpió limpiamente; ninguna afirmación depende de un resultado inventado.
