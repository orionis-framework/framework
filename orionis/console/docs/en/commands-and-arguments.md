# Create commands and arguments

A command combines an identity (`signature`), help description, arguments, and a `handle` method. The loader combines built-in commands, classes discovered under `app_console_commands`, and fluent registrations from console routes. In the template, command classes live under `app/console/commands` and fluent routes in `routes/console.py`.

## Create an application command

Save a locally defined class under the command path:

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

The loader scans importable modules and registers only `BaseCommand` subclasses defined in that module. Importing another module's class does not rediscover it locally. Signatures use lowercase letters, digits, and an optional `:` namespace; `reports:build-daily` is valid. Give commands unique identities to avoid registration collisions.

`handle()` may request typed container dependencies. Read CLI values through `getArgument()` or receive them through Reactor dispatch. When overriding `__init__` for service injection, call `super().__init__()` to initialize `BaseCommand` state.

## Describe arguments correctly

`Argument` is an immutable validated entity feeding `argparse`. `name_or_flags` accepts a positional name or flags; `type_` converts values; `choices` restricts them; `nargs` controls cardinality; `dest` selects the command's argument key. Additional fields include `default`, `const`, `required`, `help`, `metavar`, `version`, and `extra`.

Check parsing without bootstrapping an application:

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

Orionis reserves `-h`/`--help`. `required` does not make a positional argument optional: use `nargs="?"` and a default. Boolean/const actions reject `type_`; `choices` must be a collection rather than a string; the `version` action requires version text. Invalid definitions fail during `Argument` construction, before work begins.

`getArgument("missing", default)` applies the default only when the key is absent: explicitly supplied `None` is preserved. `getArguments()` returns a shallow copy. Do not use `bool("false")` for boolean parsing; use actions such as `store_true`/`store_false`.

## Register a fluent operation

In a console route loaded by the application:

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

Call `register_reports()` while loading the route, before metadata is cached; the function wrapper lets the example be imported without a booted facade. The handler is a list containing a class and method name, rather than an arbitrary import string. Add `.arguments([...])` as needed.

## Results and diagnostics

Return an integer to control the exit code; other successful results become 0. Normal Reactor failures are logged, delegated to the failure catcher, and return 1. Help and parsing errors use `SystemExit` internally. Test invalid arguments and business results: a process ending without a traceback does not imply exit code 0.
