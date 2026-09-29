from __future__ import annotations

from dataclasses import dataclass, field

from orionis.environment import Env
from orionis.foundation.config.queue.entities.brokers import Brokers
from orionis.foundation.config.queue.entities.database import Database
from orionis.foundation.config.queue.entities.queue import Queue
from orionis.foundation.config.queue.enums.strategy import Strategy


@dataclass(frozen=True, kw_only=True)
class BootstrapQueue(Queue):
    # ----------------------------------------------------------------------------------
    # default : str, optional
    # --- Name of the default queue connection.
    # --- Uses QUEUE_CONNECTION env var or "async" if not set.
    # ----------------------------------------------------------------------------------
    default: str = field(
        default_factory=lambda: Env.get("QUEUE_CONNECTION", "async"),
    )

    # ----------------------------------------------------------------------------------
    # brokers : Brokers | dict, optional
    # --- Collection of queue broker configurations.
    # --- Accepts a Brokers instance or a dictionary.
    # ----------------------------------------------------------------------------------
    brokers: Brokers | dict = field(
        default_factory=lambda: Brokers(
            # --------------------------------------------------------------------------
            # database : Database, optional
            # --- Database broker configuration with default tables and retry.
            # --- Uses FIFO strategy and default queue name.
            # --------------------------------------------------------------------------
            database=Database(
                driver="database",
                jobs_table="jobs",
                failed_jobs_table="failed_jobs",
                queue="default",
                visibility_timeout=60,
                retry_delay=90,
                max_attempts=3,
                strategy=Strategy.FIFO.value,
            ),
        ),
    )
