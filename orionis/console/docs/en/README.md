# Console and task scheduling

The console provides application commands, validated arguments, terminal output, and an APScheduler 3 scheduler. The same commands can run through the CLI, the `Reactor` facade, or scheduled tasks.

1. [Create commands and arguments](commands-and-arguments.md): discovery, parsing, dependencies, and exit codes.
2. [Output and programmatic execution](output-and-programmatic-execution.md): prompts, tables, progress, and calls from services.
3. [Schedule tasks](task-scheduling.md): triggers, timezone, stores, listeners, and operation.
4. [Built-in commands](built-in-commands.md): generators, data operations, maintenance, and workers.

Run `python reactor list` from the application root to inspect its actual registry. The installed `orionis` executable imports `bootstrap.app` from the current directory and accepts the same arguments without requiring a local `reactor` file. Both entry points need a valid application. Python 3.14+, Rich 15, and APScheduler `>=3.11.3,<4.0` are declared dependencies.

The scheduler executes commands, while [Queues](../../../queues/docs/en/README.md) processes serialized jobs with reservations and retries. They serve different purposes and can work together.
