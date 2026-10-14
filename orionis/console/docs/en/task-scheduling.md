# Schedule tasks

The scheduler executes registered commands using APScheduler 3 triggers. It is not a job queue: it does not automatically add domain serialization, business retries, or [Queues](../../../queues/docs/en/README.md) failure history.

## Configure the application schedule

The template uses `app/console/scheduler.py`, with a `BaseScheduler` subclass. Its `tasks` method receives `ISchedule` and registers existing commands. For example, with `reports:build` defined through [commands](commands-and-arguments.md):

```python
from orionis.console.base import BaseScheduler
from orionis.console.contracts import ISchedule


class Scheduler(BaseScheduler):
    def tasks(self, schedule: ISchedule) -> None:
        schedule.command("reports:build", purpose="Daily reports")\
            .coalesce()\
            .misfireGraceTime(60)\
            .maxInstances(1)\
            .dailyAt(2, 30)
```

```shell
python reactor schedule:list
python reactor schedule:work
```

`schedule:work` loads the agenda, registers listeners, starts the service, and waits for shutdown. `tasks` may be synchronous, as in the template, or async. Scheduling is separate from importing a command class: its signature must exist in the registry.

Trigger methods (`dailyAt`, `everySeconds`, `cron`, and others) are terminal and return `bool`. Configure `purpose`, `coalesce`, `misfireGraceTime`, `maxInstances`, `randomDelay`, dates, and listeners **before** the trigger. Do not chain methods after `dailyAt`.

## Choose a trigger

| Requirement | Terminal |
|---|---|
| Short interval | `everySeconds(15)` |
| Combined intervals | `every(hours=1, minutes=30)` |
| Daily time | `dailyAt(2, 30, 0)` |
| Weekday | `everyMondayAt(...)` and equivalents. |
| One date | `onceAt(2027, 1, 10, 9, 0, 0)` |
| Cron calendar | `cron(day_of_week="mon-fri", hour="9", minute="0")` |

Minute, hour, day, and week helpers are also available, along with `startDate` and `endDate`. Use intervals for elapsed time and cron for calendar scheduling. Do not assume identical behavior around daylight-saving changes. Timezone comes from `app.timezone`, normally `APP_TIMEZONE`, defaulting to `UTC`.

Fluent tasks are stored by **command signature**. Registering the same signature again replaces its pending definition; this is not an API for independent schedules sharing one signature. Use distinct commands delegating to one service when separate schedules are needed.

## Persistence and defaults

The `scheduler` section in `config/scheduler.py` uses:

| Variable | Default / effect |
|---|---|
| `TASKS_STORE` | `memory`; alternatives are `redis`, `database`. |
| `TASKS_MAX_INSTANCES` | 1 concurrent instance per task within the scheduler. |
| `TASKS_COALESCE` | `True`, collapses missed executions. |
| `TASKS_MISFIRE_GRACE_TIME` | 30 seconds of lateness tolerance. |
| `TASKS_REPLACE_EXISTING` | `True`, replaces persisted tasks on restart. |
| `TASKS_JITTER` | 0 seconds of randomized delay. |

Redis uses `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_TASKS_KEY` (`scheduler:tasks`), and `REDIS_RUN_TIMES_KEY` (`scheduler:run_times`). Database uses `DB_TASK_CONNECTION` and `DB_TASK_TABLE` (`scheduler_tasks`). That store uses a **synchronous** SQLAlchemy path and needs the corresponding extra's sync driver; it does not share an async request transaction. Redshift is rejected because it lacks enforced uniqueness and indexes.

`memory` disappears when the process ends. A persistent store retains definitions, but does not itself establish a distributed leader or guarantee one execution across processes. Run one responsible scheduler per agenda unless an external architecture has been verified; `maxInstances(1)` is not a global mutex. Keep `replace_existing=True` to restart with already persisted identities.

## Events, state, and shutdown

`BaseScheduler` offers `onStarted`, `onPaused`, `onResumed`, and `onShutdown`. For task events use `.on(event, callback)` or `registerListener` with `BaseTaskListener`; enum `TaskEvent` and `SchedulerEvent` select events, while entities with the same names carry event data. Keep their imports distinct.

The service provides async `boot()` and `info()`; `state`, `isRunning`, `isPaused`, `isStopped`, `pauseTask`, `resumeTask`, `removeTask`, `removeAllTasks`, `pause`, and `resume` provide control. `shutdown()` requests stopping and `await wait()` waits for completion; managed listener coroutines are drained during shutdown. Adding tasks after startup raises `RuntimeError` from `command()`.

A misfire or interruption does not automatically create a business retry. Make commands idempotent, observe their exit codes, and use jobs when explicit leases and retries are required.
