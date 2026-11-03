"""Define the contract for schedule store implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apscheduler.jobstores.redis import RedisJobStore
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from orionis.foundation.config.scheduler.entities.scheduler import (
        Scheduler as ConfigScheduler,
    )

class IScheduleStore(ABC):
    """Define the contract for schedule store implementations."""

    @property
    @abstractmethod
    def store(self) -> str:
        """
        Get the configured job store type.

        Returns
        -------
        str
            The job store type (e.g., 'redis', 'database').
        """

    @property
    @abstractmethod
    def config(self) -> ConfigScheduler:
        """
        Get the full scheduler configuration entity.

        Returns
        -------
        orionis.foundation.config.scheduler.Scheduler
            The scheduler configuration (store, jitter, max_instances,
            misfire_grace_time, coalesce, replace_existing, etc.).
        """

    @abstractmethod
    def redis(self) -> RedisJobStore:
        """
        Create a Redis job store for the scheduler.

        Returns
        -------
        ``apscheduler.jobstores.redis.RedisJobStore``
            A configured Redis job store instance.

        Raises
        ------
        RuntimeError
            If the Redis store configuration is not set.
        """

    @abstractmethod
    def database(self) -> SQLAlchemyJobStore:
        """
        Create a database job store for the scheduler.

        Returns
        -------
        ``apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore``
            A configured SQLAlchemy job store instance.

        Raises
        ------
        RuntimeError
            If the database store configuration is not set.
        orionis.database.MissingDatabaseDependencyException
            If the resolved driver package is not installed.
        """

    @abstractmethod
    async def migrate(self) -> None:
        """
        Create the configured database job table without starting the scheduler.

        Returns
        -------
        None
            Create missing native storage and preserve existing job data.

        Raises
        ------
        RuntimeError
            If database storage is absent or the backend is unsupported.
        orionis.database.DatabaseException
            If the connection, driver, or schema creation fails.
        """
