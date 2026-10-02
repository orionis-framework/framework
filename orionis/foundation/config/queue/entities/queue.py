from dataclasses import dataclass, field, fields
from orionis.environment import Env
from orionis.foundation.config.queue.entities.connections import Connections
from orionis.foundation.config.queue.entities.database import Database
from orionis.foundation.config.queue.entities.failed import Failed
from orionis.foundation.config.queue.entities.redis import Redis
from orionis.foundation.config.queue.entities.sync import Sync
from orionis.foundation.config.queue.entities.worker import Worker
from orionis.foundation.config.validation import validate_name
from orionis.support.entities.base import BaseEntity

_CONNECTION_ENTITIES = {"sync": Sync, "database": Database, "redis": Redis}

@dataclass(frozen=True, kw_only=True, slots=True)
class Queue(BaseEntity):
    """
    Configure named queue connections, failure storage, and workers.

    Parameters
    ----------
    default : str
        Default connection name, read from ``QUEUE_CONNECTION``.
    connections : Connections | dict
        Conventional connections or named backends converted to typed entities.
    failed : Failed | dict
        Database connection and table used to preserve failed jobs.
    worker : Worker | dict
        Default concurrency, polling interval, timeout, tries, and backoff.
    """

    default: str = field(
        default_factory=lambda: Env.get("QUEUE_CONNECTION", "sync"),
        metadata={
            "description": "Default queue connection name.",
            "default": "sync",
        },
    )

    connections: Connections | dict[str, Sync | Database | Redis | dict] = field(
        default_factory=Connections,
        metadata={
            "description": "Named queue connection settings.",
            "default": lambda: Connections().toDict(),
        },
    )

    failed: Failed | dict = field(
        default_factory=Failed,
        metadata={
            "description": "Failed-job database storage.",
            "default": lambda: Failed().toDict(),
        },
    )

    worker: Worker | dict = field(
        default_factory=Worker,
        metadata={
            "description": "Queue worker defaults.",
            "default": lambda: Worker().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Normalize nested entities and reject invalid worker leases.

        Returns
        -------
        None
            Store typed settings and validate their relationships.

        Raises
        ------
        TypeError
            If settings or durations have invalid types.
        ValueError
            If identifiers, drivers, defaults, or lease relationships are invalid.
        """
        super().__post_init__()
        validate_name(self.default, "default")
        worker = self.__normalizeWorker()
        failed = self.__normalizeFailed()
        connections = self.__normalizeConnections()
        if self.default not in connections:
            message = "The default queue connection must be declared in 'connections'."
            raise ValueError(message)
        self.__validateConnections(connections, worker, failed)

    def __normalizeWorker(self) -> Worker:
        """
        Convert worker mappings to a validated immutable entity.

        Returns
        -------
        Worker
            Validated worker defaults.

        Raises
        ------
        TypeError
            If settings have an unexpected type or unsupported fields.
        ValueError
            If a worker limit or duration is invalid.
        """
        value = self.worker
        if isinstance(value, dict):
            value = Worker(**value)
        if not isinstance(value, Worker):
            message = "'worker' must be a Worker or dictionary."
            raise TypeError(message)
        object.__setattr__(self, "worker", value)
        return value

    def __normalizeFailed(self) -> Failed:
        """
        Convert failure storage mappings to a validated immutable entity.

        Returns
        -------
        Failed
            Validated failed-job storage.

        Raises
        ------
        TypeError
            If settings have an unexpected type or unsupported fields.
        ValueError
            If a database identifier is invalid.
        """
        value = self.failed
        if isinstance(value, dict):
            value = Failed(**value)
        if not isinstance(value, Failed):
            message = "'failed' must be a Failed or dictionary."
            raise TypeError(message)
        object.__setattr__(self, "failed", value)
        return value

    def __normalizeConnections(self) -> dict[str, Sync | Database | Redis]:
        """
        Validate conventional or named connections as typed entities.

        Returns
        -------
        dict[str, Sync | Database | Redis]
            Validated connections indexed by their configured names.

        Raises
        ------
        TypeError
            If a connection has an unexpected type or unsupported fields.
        ValueError
            If a connection name, driver, or nested setting is invalid.
        """
        if isinstance(self.connections, Connections):
            supplied_connections = {
                item.name: getattr(self.connections, item.name)
                for item in fields(self.connections)
            }
        elif isinstance(self.connections, dict):
            supplied_connections = self.connections
        else:
            message = "'connections' must be a Connections or dictionary."
            raise TypeError(message)
        normalized: dict[str, Sync | Database | Redis] = {}
        for name, supplied in supplied_connections.items():
            validate_name(name, "connection name")
            if isinstance(supplied, dict):
                driver = supplied.get("driver", name)
                if not isinstance(driver, str) or driver not in _CONNECTION_ENTITIES:
                    message = "Queue drivers must be 'sync', 'database', or 'redis'."
                    raise ValueError(message)
                configuration = _CONNECTION_ENTITIES[driver](**supplied)
            elif isinstance(supplied, (Sync, Database, Redis)):
                configuration = supplied
            else:
                message = "Each queue connection must be a connection entity or dict."
                raise TypeError(message)
            normalized[name] = configuration
        if isinstance(self.connections, dict):
            object.__setattr__(self, "connections", normalized)
        return normalized

    @staticmethod
    def __validateConnections(
        connections: dict[str, Sync | Database | Redis],
        worker: Worker,
        failed: Failed,
    ) -> None:
        """
        Validate reservation leases and isolate failure storage.

        Parameters
        ----------
        connections : dict[str, Sync | Database | Redis]
            Validated named connection entities.
        worker : Worker
            Validated execution defaults.
        failed : Failed
            Validated failed-job storage.

        Returns
        -------
        None
            Check relationships across the configuration entities.

        Raises
        ------
        ValueError
            If a lease is unsafe or persistent storage namespaces overlap.
        """
        for name, settings in connections.items():
            if worker.timeout >= settings.retry_after:
                message = (
                    f"Queue connection '{name}' requires worker.timeout "
                    "to be strictly less than retry_after."
                )
                raise ValueError(message)
            if (
                isinstance(settings, Database)
                and settings.connection == failed.connection
                and settings.table == failed.table
            ):
                message = "Failed-job storage must use a table distinct from jobs."
                raise ValueError(message)
        Queue.__validateStorageNamespaces(connections)

    @staticmethod
    def __validateStorageNamespaces(
        connections: dict[str, Sync | Database | Redis],
    ) -> None:
        """
        Require distinct persistent storage for named durable connections.

        Parameters
        ----------
        connections : dict[str, Sync | Database | Redis]
            Validated named connection entities.

        Returns
        -------
        None
            Require independent tables or Redis prefixes for durable connections.

        Raises
        ------
        ValueError
            If two connections use the same persistent storage namespace.
        """
        namespaces: dict[tuple[object, ...], str] = {}
        for name, settings in connections.items():
            if isinstance(settings, Sync):
                continue
            if isinstance(settings, Database):
                namespace = ("database", settings.connection, settings.table)
            else:
                namespace = (
                    "redis", settings.endpoint, settings.port, settings.db,
                    settings.prefix,
                )
            if namespace in namespaces:
                message = (
                    f"Queue connections '{namespaces[namespace]}' and '{name}' "
                    "must use distinct tables or Redis prefixes."
                )
                raise ValueError(message)
            namespaces[namespace] = name
