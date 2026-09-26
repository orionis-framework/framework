from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.scheduler import (
    Database, Drivers, Memory, Redis, Scheduler, Stores,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapScheduler(Scheduler):
    # ----------------------------------------------------------------------------------
    # store : Drivers | str, optional
    # --- The default task store used by the task scheduler.
    # --- Defaults to the TASKS_STORE env var or "memory".
    # ----------------------------------------------------------------------------------
    store: Drivers | str = field(
        default_factory=lambda: Env.get("TASKS_STORE", Drivers.MEMORY),
    )

    # ----------------------------------------------------------------------------------
    # stores : Stores | dict, optional
    # --- Configuration for all available scheduler task stores.
    # ----------------------------------------------------------------------------------
    stores: Stores | dict = field(
        default_factory=lambda: Stores(
            # --------------------------------------------------------------------------
            # memory : Memory, optional
            # --- In-memory task store (default driver, process-scoped).
            # --------------------------------------------------------------------------
            memory=Memory(),
            # --------------------------------------------------------------------------
            # redis : Redis, optional
            # --- Redis task store.
            # --------------------------------------------------------------------------
            redis=Redis(
                host=Env.get("REDIS_HOST", "localhost"),
                port=Env.get("REDIS_PORT", 6379),
                db=Env.get("REDIS_DB", 0),
                password=Env.get("REDIS_PASSWORD", None),
                key=Env.get("REDIS_TASKS_KEY", "scheduler:tasks"),
                run_times_key=Env.get("REDIS_RUN_TIMES_KEY", "scheduler:run_times"),
            ),
            # --------------------------------------------------------------------------
            # database : Database, optional
            # --- Database task store.
            # --------------------------------------------------------------------------
            database=Database(
                connection=Env.get("DB_TASK_CONNECTION", None),
                table=Env.get("DB_TASK_TABLE", "scheduler_tasks"),
            ),
        ),
    )

    # ----------------------------------------------------------------------------------
    # max_instances : int, optional
    # --- Maximum number of concurrently running instances allowed for a
    # --- single scheduled task.
    # --- Defaults to the TASKS_MAX_INSTANCES env var or 1.
    # ----------------------------------------------------------------------------------
    max_instances: int = field(
        default_factory=lambda: Env.get("TASKS_MAX_INSTANCES", 1),
    )

    # ----------------------------------------------------------------------------------
    # coalesce : bool, optional
    # --- Whether missed runs of a task are collapsed into a single run.
    # --- Defaults to the TASKS_COALESCE env var or True.
    # ----------------------------------------------------------------------------------
    coalesce: bool = field(
        default_factory=lambda: Env.get("TASKS_COALESCE", True),
    )

    # ----------------------------------------------------------------------------------
    # misfire_grace_time : int | None, optional
    # --- Number of seconds a task is allowed to run late before it is
    # --- considered misfired.
    # --- Defaults to the TASKS_MISFIRE_GRACE_TIME env var or 30.
    # ----------------------------------------------------------------------------------
    misfire_grace_time: int | None = field(
        default_factory=lambda: Env.get("TASKS_MISFIRE_GRACE_TIME", 30),
    )

    # ----------------------------------------------------------------------------------
    # replace_existing : bool, optional
    # --- Whether adding a task with an already registered id replaces the
    # --- previous definition. Must stay True for persistent job stores
    # --- (database/redis), otherwise restarting schedule:work raises
    # --- ConflictingIdError for every task already persisted from a
    # --- previous run.
    # --- Defaults to the TASKS_REPLACE_EXISTING env var or True.
    # ----------------------------------------------------------------------------------
    replace_existing: bool = field(
        default_factory=lambda: Env.get("TASKS_REPLACE_EXISTING", True),
    )

    # ----------------------------------------------------------------------------------
    # jitter : int, optional
    # --- Maximum number of seconds of random delay applied to task
    # --- execution to avoid thundering-herd effects.
    # --- Defaults to the TASKS_JITTER env var or 0.
    # ----------------------------------------------------------------------------------
    jitter: int = field(
        default_factory=lambda: Env.get("TASKS_JITTER", 0),
    )
