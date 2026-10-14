# Crear comandos y argumentos

Un comando reúne una identidad (`signature`), documentación de ayuda, argumentos y un método `handle`. El loader combina comandos incluidos, clases descubiertas en `app_console_commands` y registros fluidos de las rutas de consola. En la plantilla, la ruta de clases corresponde a `app/console/commands` y las rutas fluidas a `routes/console.py`.

## Crear un comando de aplicación

Guarda una clase local al módulo bajo la ruta de comandos:

```python
from typing import ClassVar
from orionis.console import Argument
from orionis.console.base import BaseCommand


class GreetCommand(BaseCommand):
    signature = "app:greet"
    description = "Print a greeting."
    arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="name", help="Name to greet."),
        Argument(name_or_flags=("-n", "--times"), type_=int, default=1),
        Argument(name_or_flags="--quiet", action="store_true", default=False),
    ]

    async def handle(self) -> int:
        count = self.getArgument("times")
        if count < 1:
            self.error("--times must be positive", timestamp=False)
            return 2
        if not self.getArgument("quiet"):
            for _ in range(count):
                self.writeLine(f"Hello, {self.getArgument('name')}!")
        return 0
```

```shell
python reactor app:greet Ada --times 2
python reactor app:greet --help
```

El loader escanea módulos importables y solo registra clases definidas en ese módulo que hereden `BaseCommand`. No basta con importar una clase ajena en otro archivo para descubrirla de nuevo. Las firmas usan minúsculas, dígitos y, opcionalmente, un namespace separado por `:`; un nombre como `reports:build-daily` es válido. Asigna identidades únicas para evitar colisiones entre las fuentes de registro.

`handle()` puede solicitar dependencias tipadas al contenedor. Los valores CLI se consultan con `getArgument()` o se reciben según el despacho del reactor. Si sobrescribes `__init__` para inyectar servicios, llama a `super().__init__()` para inicializar el estado de `BaseCommand`.

## Describir argumentos correctamente

`Argument` es una entidad validada e inmutable que alimenta `argparse`. `name_or_flags` recibe un nombre posicional o flags; `type_` transforma valores; `choices` los restringe; `nargs` controla cantidad; `dest` fija el nombre leído por el comando. `default`, `const`, `required`, `help`, `metavar`, `version` y `extra` completan la definición.

Puedes comprobar el parsing sin arrancar una aplicación:

```python
import argparse
from orionis.console import Argument

parser = argparse.ArgumentParser(add_help=False)
Argument(
    name_or_flags=("-f", "--format"),
    choices=["json", "csv"], default="json", dest="format_name",
).addToParser(parser)
assert vars(parser.parse_args(["--format", "csv"])) == {"format_name": "csv"}
```

Orionis reserva `-h`/`--help`. `required` no vuelve opcional un posicional: para ello usa `nargs="?"` y un default. Acciones booleanas/const no admiten `type_`; `choices` debe ser una colección, no un string; la acción `version` necesita un texto `version`. Definiciones inválidas fallan al construir `Argument`, antes de ejecutar trabajo.

`getArgument("missing", default)` usa el default solo si falta la clave: un `None` proporcionado explícitamente se conserva. `getArguments()` devuelve una copia superficial. No interpretes `bool("false")` como parsing de booleanos; usa acciones como `store_true`/`store_false`.

## Registrar una operación fluida

En una ruta de consola cargada por la aplicación:

```python
from orionis.support.facades import Reactor


class ReportHandler:
    async def run(self) -> int:
        return 0


def register_reports() -> None:
    Reactor.command("reports:build", [ReportHandler, "run"]).description(
        "Build reports."
    ).timestamp(enabled=False)
```

Invoca `register_reports()` durante la carga de la ruta, antes de cachear metadatos; el bloque muestra la función para que importar el ejemplo no requiera una facade inicializada. El handler es una lista de clase y nombre de método, no una cadena de import arbitraria. Añade `.arguments([...])` cuando lo necesites.

## Resultado y diagnóstico

Devuelve un entero para controlar el exit code; otros resultados correctos se normalizan a 0. Un fallo normal del flujo Reactor se registra, se delega al capturador de errores y devuelve 1. La ayuda y los errores de parsing utilizan `SystemExit` internamente. Prueba tanto argumentos inválidos como retornos de negocio: que el proceso termine sin traceback no implica que su código de salida sea 0.
