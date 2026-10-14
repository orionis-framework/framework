# Output and programmatic execution

## Write useful output

`BaseCommand` inherits `Console`, so commands call `self.writeLine()`, `self.success()`, or `self.table()` directly. Outside commands, construct `Console` from `orionis.console.output.console`.

```python
from orionis.console.output.console import Console

console = Console()
console.writeLine("Import summary")
console.table(["Status", "Rows"], [["created", 12], ["skipped", 3]])
console.success("Finished", timestamp=False)
```

`success`, `info`, `warning`, `fail`, and `error` print status messages with optional timestamps. `textSuccess`, `textInfo`, `textWarning`, `textError`, Bold variants, `textMuted`, and `textUnderline` print inline styles. `write`, `writeLine`, `line`, and `newLine` organize text; `clear` and `clearLine` control the terminal.

Output methods are synchronous. Calling them from `async handle()` does not make terminal I/O asynchronous. Avoid printing one line per row during large jobs; summarize batches. Keep passwords, tokens, and sensitive payloads out of error output.

## Request input and control the process

`ask(question)` returns text, `secret(question)` hides input, and `confirm(question, default=False)` returns a boolean. `choice(question, choices, default_index=0)` and `anticipate(question, options, default=None)` support selection. Prompts block: offer explicit arguments for automation and do not assume stdin is available.

`exitSuccess()` and `exitError()` raise `SystemExit`; return an integer from `handle` when you intend to report a code to Reactor. `exception(error)` renders diagnostics; `dump(...)` and `Dumper` help development. `dd` terminates after dumping and should not remain in operational code.

## Display progress

```python
from orionis.console.dynamic.progress_bar import ProgressBar

bar = ProgressBar(total=3, width=12)
bar.start()
for _ in range(3):
    bar.advance()
bar.finish()
```

Total and width must be positive. The bar redraws one terminal using carriage returns; it is neither a business event nor durable logging. Do not mix concurrent bars on one stdout. `await console.sleep(seconds)` provides cooperative delays; that async method differs from synchronous prompts and printing.

## Call commands from code

With the application booted and `app:greet` registered as shown in [commands](commands-and-arguments.md):

```python
from orionis.support.facades import Reactor


async def run_greeting() -> int:
    if not await Reactor.hasCommand("app:greet"):
        return 1
    return await Reactor.call("app:greet", ["Ada", "--quiet"])
```

`call(signature, args=None)` accepts a list of strings, like the CLI. Each call opens a console-marked container scope, builds the handler, and invokes it with DI. Failures are logged and passed to `ICatch`; callers normally receive 1, rather than the original exception. Inspect the code instead of relying solely on `try/except`.

`await Reactor.info()` returns sorted, cached metadata; `await Reactor.hasCommand(signature)` checks the registry. Register fluent commands before cache/boot. When changing command classes or routes with compilation enabled, the [optimization workflow](built-in-commands.md) must reflect the deployed version.

Programmatic calls do not spawn another process or isolate command effects. Put business logic in services when rich results are needed; use commands for operational orchestration and exit codes. Services can then be reused by HTTP, jobs, and commands without parsing terminal text.
