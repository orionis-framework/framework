# Salida y ejecución programática

## Escribir una salida útil

`BaseCommand` hereda `Console`, por lo que un comando puede llamar a `self.writeLine()`, `self.success()` o `self.table()` directamente. Fuera de un comando puedes construir `Console` desde `orionis.console.output.console`.

```python
from orionis.console.output.console import Console

console = Console()
console.writeLine("Import summary")
console.table(["Status", "Rows"], [["created", 12], ["skipped", 3]])
console.success("Finished", timestamp=False)
```

`success`, `info`, `warning`, `fail` y `error` son mensajes de estado con timestamp opcional. `textSuccess`, `textInfo`, `textWarning`, `textError`, variantes Bold, `textMuted` y `textUnderline` escriben estilos inline. `write`, `writeLine`, `line` y `newLine` organizan texto; `clear` y `clearLine` controlan el terminal.

Los métodos de salida son síncronos. Llamarlos desde `async handle()` no los convierte en I/O asíncrona. Evita imprimir una línea por fila en trabajos masivos; resume por lotes. No imprimas contraseñas, tokens ni payloads sensibles al informar errores.

## Solicitar datos y controlar el proceso

`ask(question)` devuelve texto, `secret(question)` oculta la entrada y `confirm(question, default=False)` devuelve booleano. `choice(question, choices, default_index=0)` y `anticipate(question, options, default=None)` ayudan a elegir. Son interacciones bloqueantes: para automatización ofrece argumentos explícitos y no dependas de stdin disponible.

`exitSuccess()` y `exitError()` lanzan `SystemExit`; si tu intención es devolver un código al reactor, devuelve un entero desde `handle`. `exception(error)` muestra diagnósticos; `dump(...)` y `Dumper` sirven para desarrollo. `dd` termina después del volcado, por lo que no debe quedar en código operativo.

## Mostrar progreso

```python
from orionis.console.dynamic.progress_bar import ProgressBar

bar = ProgressBar(total=3, width=12)
bar.start()
for _ in range(3):
    bar.advance()
bar.finish()
```

El progreso debe tener total y ancho positivos. La barra actualiza el mismo terminal mediante retorno de carro; no es un evento de negocio ni un registro durable. No mezcles varias barras concurrentes en el mismo stdout. Para pausas cooperativas existe `await console.sleep(seconds)`; no confundas ese método async con prompts y escritura síncronos.

## Llamar comandos desde código

Con la aplicación inicializada y `app:greet` registrado como en [comandos](commands-and-arguments.md):

```python
from orionis.support.facades import Reactor


async def run_greeting() -> int:
    if not await Reactor.hasCommand("app:greet"):
        return 1
    return await Reactor.call("app:greet", ["Ada", "--quiet"])
```

`call(signature, args=None)` acepta una lista de strings, como el CLI. Cada llamada abre un scope de contenedor marcado como consola, construye el handler e invoca el método con DI. Un fallo se registra y se pasa a `ICatch`; el llamador recibe 1 en el flujo normal, no necesariamente la excepción original. Comprueba el código y no uses `try/except` como única detección del fallo.

`await Reactor.info()` devuelve metadatos ordenados y cacheados; `await Reactor.hasCommand(signature)` consulta el registro. Registra comandos fluidos antes de ese cache/boot. Si cambias clases o rutas de consola con compilación activa, el flujo de [optimización](built-in-commands.md) debe reflejar la versión desplegada.

Las llamadas programáticas no crean un nuevo proceso ni aíslan efectos del comando. Comparte lógica de negocio en servicios cuando necesites resultados ricos; usa comandos para orquestación operativa y códigos de salida. Esto facilita reutilizar el servicio desde HTTP, jobs y comandos sin depender de parsing de texto de terminal.
