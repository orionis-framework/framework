from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.queue import (
    Connections, Database, Drivers, Failed, Queue, Redis, Sync, Worker,
)

@dataclass(frozen=True, kw_only=True, slots=True)
class BootstrapQueue(Queue):

    # ----------------------------------------------------------------------------------
    # default : str, optional
    # --- The default queue connection name.
    # --- Uses the QUEUE_CONNECTION env var or "sync" if not set.
    # ----------------------------------------------------------------------------------
    default: str = field(
        default_factory=lambda: Env.get("QUEUE_CONNECTION", Drivers.SYNC),
    )

    # ----------------------------------------------------------------------------------
    # connections : Connections | dict, optional
    # --- The available queue backends and their default logical queues.
    # --- Configure each backend's environment keys and fallback values here.
    # --- Named durable connections must use independent storage namespaces.
    # ----------------------------------------------------------------------------------
    connections: Connections | dict[str, Sync | Database | Redis | dict] = field(
        default_factory=lambda: Connections(

            # --------------------------------------------------------------------------
            # sync : Sync, optional
            # --- Execute jobs immediately in the dispatching process.
            # --- Uses QUEUE_SYNC_QUEUE and QUEUE_SYNC_RETRY_AFTER.
            # --------------------------------------------------------------------------
            sync=Sync(
                queue=Env.get("QUEUE_SYNC_QUEUE", "default"),
                retry_after=Env.get("QUEUE_SYNC_RETRY_AFTER", 90.0),
            ),

            # --------------------------------------------------------------------------
            # database : Database, optional
            # --- Persist jobs using a framework database connection.
            # --- Uses QUEUE_DB_CONNECTION and QUEUE_TABLE environment variables.
            # --- Queue and reservation use QUEUE_DB_QUEUE and QUEUE_DB_RETRY_AFTER.
            # --------------------------------------------------------------------------
            database=Database(
                connection=Env.get("QUEUE_DB_CONNECTION", None),
                table=Env.get("QUEUE_TABLE", "jobs"),
                queue=Env.get("QUEUE_DB_QUEUE", "default"),
                retry_after=Env.get("QUEUE_DB_RETRY_AFTER", 90.0),
            ),

            # --------------------------------------------------------------------------
            # redis : Redis, optional
            # --- Persist jobs in Redis using separate connection fields.
            # --- Uses REDIS_HOST, REDIS_PORT, REDIS_DB, and REDIS_PASSWORD.
            # --- Namespace, queue, and reservation use QUEUE_REDIS_* keys.
            # --- Use distinct prefixes for independent named Redis backends.
            # --------------------------------------------------------------------------
            redis=Redis(
                endpoint=Env.get("REDIS_HOST", "127.0.0.1"),
                port=Env.get("REDIS_PORT", 6379),
                db=Env.get("REDIS_DB", 0),
                password=Env.get("REDIS_PASSWORD", None),
                prefix=Env.get("QUEUE_REDIS_PREFIX", "orionis:queues"),
                queue=Env.get("QUEUE_REDIS_QUEUE", "default"),
                retry_after=Env.get("QUEUE_REDIS_RETRY_AFTER", 90.0),
            ),
        ),
    )

    # ----------------------------------------------------------------------------------
    # failed : Failed | dict, optional
    # --- Database storage for jobs that exhaust their retry budget.
    # --- Uses QUEUE_FAILED_DB_CONNECTION and QUEUE_FAILED_TABLE.
    # --- Use a table distinct from jobs on the same database connection.
    # ----------------------------------------------------------------------------------
    failed: Failed | dict = field(
        default_factory=lambda: Failed(
            connection=Env.get("QUEUE_FAILED_DB_CONNECTION", None),
            table=Env.get("QUEUE_FAILED_TABLE", "failed_jobs"),
        ),
    )

    # ----------------------------------------------------------------------------------
    # worker : Worker | dict, optional
    # --- Default concurrency, polling interval, timeout, and retry policy.
    # --- Uses QUEUE_WORKER_* environment variables for every worker setting.
    # --- Durations are in seconds; tries includes the first attempt.
    # --- Keep timeout strictly below every connection's retry_after.
    # --- Backoff delays apply between failed attempts.
    # ----------------------------------------------------------------------------------
    worker: Worker | dict = field(
        default_factory=lambda: Worker(
            concurrency=Env.get("QUEUE_WORKER_CONCURRENCY", 1),
            sleep=Env.get("QUEUE_WORKER_SLEEP", 1.0),
            timeout=Env.get("QUEUE_WORKER_TIMEOUT", 60.0),
            tries=Env.get("QUEUE_WORKER_TRIES", 3),
            backoff=Env.get("QUEUE_WORKER_BACKOFF", (0.0,)),
        ),
    )
