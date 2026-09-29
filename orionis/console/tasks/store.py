from typing import Any
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.engine.url import URL
from orionis.console.contracts.store import IScheduleStore
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.dialect import (
    build_engine_url,
    engine_options,
    missing_dependency_error,
    resolve_driver,
)
from orionis.foundation.config.scheduler.entities.database import Database
from orionis.foundation.config.scheduler.entities.redis import Redis
from orionis.foundation.config.scheduler.entities.scheduler import (
    Scheduler as ConfigScheduler,
)
from orionis.foundation.contracts.application import IApplication

class ScheduleStore(IScheduleStore):

    # ruff: noqa: TC001, TC002

    def __init__(
        self,
        app: IApplication,
        db_manager: IConnectionManager,
    ) -> None:
        """
        Initialize the schedule store.

        Parameters
        ----------
        app : IApplication
            The application instance.
        db_manager : IConnectionManager
            The database connection manager.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Cache the application and build the scheduler configuration.
        self.__application: IApplication = app
        self.__scheduler_conf: ConfigScheduler = ConfigScheduler(
            **self.__application.config("scheduler"),
        )
        self._db_manager: IConnectionManager = db_manager

    @property
    def store(self) -> str:
        """
        Get the configured job store type.

        Returns
        -------
        str
            The job store type (e.g., 'redis', 'database').
        """
        return self.__scheduler_conf.store

    @property
    def config(self) -> ConfigScheduler:
        """
        Get the full scheduler configuration entity.

        Returns
        -------
        ConfigScheduler
            The scheduler configuration (store, jitter, max_instances,
            misfire_grace_time, coalesce, replace_existing, etc.).
        """
        return self.__scheduler_conf

    def redis(self) -> RedisJobStore:
        """
        Create a Redis job store for the scheduler.

        Returns
        -------
        RedisJobStore
            A configured Redis job store instance.

        Raises
        ------
        RuntimeError
            If the Redis store configuration is not set.
        """
        # Validate that the Redis store configuration is present.
        redis_store: Redis | None = self.__scheduler_conf.stores.redis
        if redis_store is None:
            error_msg = (
                "The scheduler is configured to use the 'redis' job "
                "store, but 'scheduler.stores.redis' is not configured."
            )
            raise RuntimeError(error_msg)

        # Build the job store from the resolved Redis configuration.
        return RedisJobStore(
            jobs_key=redis_store.key,
            run_times_key=redis_store.run_times_key,
            host=redis_store.host,
            port=redis_store.port,
            db=redis_store.db,
            password=redis_store.password,
        )

    def database(self) -> SQLAlchemyJobStore:
        """
        Create a database job store for the scheduler.

        Returns
        -------
        SQLAlchemyJobStore
            A configured SQLAlchemy job store instance.

        Raises
        ------
        RuntimeError
            If the database store configuration is not set.
        MissingDatabaseDependencyException
            If the resolved driver package is not installed.
        """
        # Validate that the database store configuration is present.
        database_store: Database | None = self.__scheduler_conf.stores.database
        if database_store is None:
            error_msg = (
                "The scheduler is configured to use the 'database' job "
                "store, but 'scheduler.stores.database' is not configured."
            )
            raise RuntimeError(error_msg)

        # Resolve the connection config and derive the sync engine URL.
        config: dict[str, Any] = self._db_manager.configFor(database_store.connection)
        url: URL = build_engine_url(config, sync=True)
        options: dict[str, Any] = engine_options(config, sync=True)
        try:
            # Build the job store; the sync driver may be missing.
            return SQLAlchemyJobStore(
                url=url,
                tablename=database_store.table,
                engine_options=options,
            )
        except ModuleNotFoundError as exc:
            # Map the missing package to an actionable framework error.
            raise missing_dependency_error(
                resolve_driver(config), exc, sync=True,
            ) from exc
