# Consola y programación de tareas

La consola ofrece comandos de aplicación, argumentos validados, salida de terminal y un scheduler basado en APScheduler 3. Los mismos comandos pueden ejecutarse desde el proceso CLI, mediante la facade `Reactor` o como tareas programadas.

1. [Crear comandos y argumentos](commands-and-arguments.md): descubrimiento, parsing, dependencias y códigos de salida.
2. [Salida y ejecución programática](output-and-programmatic-execution.md): prompts, tablas, progreso y llamadas desde otros servicios.
3. [Programar tareas](task-scheduling.md): triggers, zona horaria, stores, listeners y operación.
4. [Comandos incluidos](built-in-commands.md): recorrido por generadores, datos, mantenimiento y workers.

Ejecuta `python reactor list` desde la raíz de la aplicación para conocer su registro real. El ejecutable instalado `orionis` entra en `bootstrap.app` del directorio actual y admite los mismos argumentos; no necesita un archivo `reactor` propio. Ambos caminos requieren una aplicación válida. Python 3.14+, Rich 15 y APScheduler `>=3.11.3,<4.0` forman parte de las dependencias declaradas.

El scheduler ejecuta comandos, mientras [Queues](../../../queues/docs/es/README.md) procesa jobs serializados con reservas y reintentos. Son herramientas distintas que pueden colaborar.
