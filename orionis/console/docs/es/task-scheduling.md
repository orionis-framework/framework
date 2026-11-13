# Programar tareas

El scheduler ejecuta comandos registrados con triggers de APScheduler 3. No es una cola de jobs: no añade automáticamente serialización de dominio, reintentos de negocio ni historial de fallos de [Queues](../../../queues/docs/es/README.md).

## Configurar la agenda de la aplicación

La plantilla usa `app/console/scheduler.py`, con una clase que hereda `BaseScheduler`. Su método `tasks` recibe `ISchedule` y registra comandos existentes. Por ejemplo, con `reports:build` definido mediante [comandos](commands-and-arguments.md):

```python
from orionis.console.base import BaseScheduler
from orionis.console.contracts import ISchedule


class Scheduler(BaseScheduler):
    def tasks(self, schedule: ISchedule) -> None:
        schedule.command(
            "reports:build", purpose="Daily reports"
        ).coalesce().misfireGraceTime(60).maxInstances(1).dailyAt(2, 30)
```

```shell
python reactor schedule:list
python reactor schedule:work
```

`schedule:work` carga la agenda, registra listeners, inicia el servicio y espera hasta la parada. `tasks` puede ser síncrono, como en la plantilla, o async. Es distinto de importar una clase de comando: la firma debe existir en el registro.

La selección temporal (`dailyAt`, `everySeconds`, `cron`, etc.) es terminal y devuelve `bool`. Configura `purpose`, `coalesce`, `misfireGraceTime`, `maxInstances`, `randomDelay`, fechas y listeners **antes** del trigger. No encadenes otro método después de `dailyAt`.

## Elegir un trigger

| Necesidad | Terminal |
|---|---|
| Intervalo breve | `everySeconds(15)` |
| Intervalos combinados | `every(hours=1, minutes=30)` |
| Hora diaria | `dailyAt(2, 30, 0)` |
| Día de semana | `everyMondayAt(...)`, y equivalentes |
| Fecha única | `onceAt(2027, 1, 10, 9, 0, 0)` |
| Calendario cron | `cron(day_of_week="mon-fri", hour="9", minute="0")` |

Existen helpers de minutos, horas, días y semanas, además de `startDate` y `endDate`. Usa intervalos para tiempo transcurrido y cron para calendario. No asumas que ambos responden igual a cambios de horario estacional. La zona viene de `app.timezone`, normalmente `APP_TIMEZONE`, con default `UTC`.

La agenda fluida guarda tareas por **firma de comando**. Registrar otra vez la misma firma reemplaza esa definición pendiente; no es una API para crear dos horarios independientes para una firma. Usa comandos con identidades distintas que deleguen al mismo servicio si necesitas agendas separadas.

`TASKS_JITTER` se aplica a los triggers que admiten jitter, no solo a la metadata mostrada. Un `randomDelay(0)` de la tarea prevalece sobre ese default. `onceAt`, `everySeconds`, `everyMinuteAt`, `everyMinutesAt`, `hourlyAt` y `everyHoursAt` conservan horarios exactos y no heredan jitter; sus atajos conservan la misma política. Un retraso positivo explícito entra en conflicto con esos horarios y produce `ValueError`.

## Persistencia y valores predeterminados

La sección `scheduler` de `config/scheduler.py` usa:

| Variable | Default / efecto |
|---|---|
| `TASKS_STORE` | `memory`; alternativas `redis`, `database`. |
| `TASKS_MAX_INSTANCES` | 1 instancia concurrente por tarea en el scheduler. |
| `TASKS_COALESCE` | `True`, agrupa ejecuciones atrasadas. |
| `TASKS_MISFIRE_GRACE_TIME` | 30 segundos de tolerancia. |
| `TASKS_REPLACE_EXISTING` | `True`, reemplaza tareas persistidas al reiniciar. |
| `TASKS_JITTER` | 0 segundos de dispersión aleatoria. |

Redis utiliza `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_TASKS_KEY` (`scheduler:tasks`) y `REDIS_RUN_TIMES_KEY` (`scheduler:run_times`). Database utiliza `DB_TASK_CONNECTION` y `DB_TASK_TABLE` (`scheduler_tasks`). Ese store crea una ruta SQLAlchemy **síncrona**, por lo que necesita el driver sync del extra correspondiente; no comparte la transacción async de una petición. Redshift se rechaza por falta de unicidad impuesta e índices.

`memory` se pierde al terminar el proceso. Un store persistente conserva definiciones, pero no establece por sí mismo un líder distribuido ni una garantía de ejecución única entre procesos. Opera una instancia responsable de cada agenda salvo arquitectura externa probada; `maxInstances(1)` no es un mutex global. Mantén `replace_existing=True` para reiniciar con identidades ya persistidas.

## Eventos, estado y apagado

`BaseScheduler` ofrece `onStarted`, `onPaused`, `onResumed` y `onShutdown`. Para eventos de tarea usa `.on(event, callback)` o `registerListener` con `BaseTaskListener`; los tipos `TaskEvent` y `SchedulerEvent` de enums seleccionan eventos, mientras entidades del mismo nombre transportan datos. No confundas ambos imports.

El servicio expone `boot()` e `info()` async; `state`, `isRunning`, `isPaused`, `isStopped`, `pauseTask`, `resumeTask`, `removeTask`, `removeAllTasks`, `pause` y `resume` permiten control. `shutdown()` solicita la parada y `await wait()` espera su finalización; las coroutines de listeners se gestionan y drenan durante el apagado. No se permiten nuevas tareas después de iniciar: `command()` produce `RuntimeError`.

Los listeners del ciclo de vida observan el estado ya actualizado. Un inicio fallido restaura `STOPPED`; un apagado completado limpia el seguimiento de tareas activas y pausadas. Si falla la admisión de una tarea de listener, se cierran ambas coroutines no programadas y se propaga el error de admisión.

Las llamadas concurrentes o repetidas a `boot()` comparten el scheduler activo, sin iniciar agendas duplicadas. Un inicio parcial libera sus stores y executor propios. Espera `wait()` antes de reiniciar tras el apagado; iniciar mientras el apagado está pendiente produce `RuntimeError`.

El apagado espera el callback nativo de cierre real, los finalizadores de jobs cancelados y los listeners admitidos durante ese callback. Los fallos del store nativo llegan a `wait()`; programar el callback de cierre de APScheduler no equivale a completarlo.

Una interrupción/misfire no genera automáticamente un retry de negocio. Diseña comandos idempotentes, observa sus códigos de salida y utiliza jobs cuando necesites leases y reintentos explícitos.
