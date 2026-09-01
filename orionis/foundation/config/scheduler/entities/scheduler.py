from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.foundation.config.scheduler.entities.stores import Stores
from orionis.foundation.config.scheduler.enums.drivers import Drivers
from orionis.support.entities.base import BaseEntity

# Pre-computed frozenset of valid driver names for O(1) membership checks
_DRIVER_NAMES: frozenset[str] = frozenset(Drivers._member_names_)

@dataclass(frozen=True, kw_only=True)
class Scheduler(BaseEntity):
    """
    Represent the task scheduler configuration for the application.

    Attributes
    ----------
    store : Drivers | str
        The default job store used by the task scheduler. Accepts a
        ``Drivers`` enum member or a plain string (e.g. ``'memory'``,
        ``'redis'``). Resolved from the ``TASKS_STORE`` environment
        variable or ``Drivers.MEMORY.value``.
    stores : Stores | dict
        Configuration for the available scheduler job stores. Defaults to
        a ``Stores`` instance backed by the in-memory job store.
    max_instances : int
        Maximum number of concurrently running instances allowed for a
        single scheduled job. Defaults to ``1``.
    coalesce : bool
        Whether missed runs of a job are collapsed into a single run.
        Defaults to ``True``.
    misfire_grace_time : int
        Number of seconds a job is allowed to run late before it is
        considered misfired. Defaults to ``30``.
    replace_existing : bool
        Whether adding a job with an already registered id replaces the
        previous definition. Defaults to ``True`` so the declarative task
        list is always reconciled against a persistent job store (e.g.
        ``database``/``redis``) on every restart, instead of raising
        ``ConflictingIdError`` for jobs that already exist from a previous
        run.
    jitter : int
        Maximum number of seconds of random delay applied to job
        execution to avoid thundering-herd effects. Defaults to ``0``.
    """

    store: Drivers | str = field(
        default_factory=lambda: Env.get("TASKS_STORE", Drivers.MEMORY.value),
        metadata={
            "description": (
                "The default job store used by the task scheduler. Can be "
                "a member of the Drivers enum or a string (e.g., 'memory', "
                "'redis')."
            ),
            "default": Drivers.MEMORY.value,
        },
    )

    stores: Stores | dict = field(
        default_factory=Stores,
        metadata={
            "description": (
                "The configuration for available scheduler job stores. "
                "Defaults to an in-memory job store."
            ),
            "default": lambda: Stores().toDict(),
        },
    )

    max_instances: int = field(
        default=1,
        metadata={
            "description": (
                "Maximum number of concurrently running instances allowed "
                "for a single scheduled job."
            ),
            "default": 1,
        },
    )

    coalesce: bool = field(
        default=True,
        metadata={
            "description": (
                "Whether missed runs of a job are collapsed into a single "
                "run."
            ),
            "default": True,
        },
    )

    misfire_grace_time: int = field(
        default=30,
        metadata={
            "description": (
                "Number of seconds a job is allowed to run late before it "
                "is considered misfired."
            ),
            "default": 30,
        },
    )

    replace_existing: bool = field(
        default=True,
        metadata={
            "description": (
                "Whether adding a job with an already registered id "
                "replaces the previous definition."
            ),
            "default": True,
        },
    )

    jitter: int = field(
        default=0,
        metadata={
            "description": (
                "Maximum number of seconds of random delay applied to job "
                "execution to avoid thundering-herd effects."
            ),
            "default": 0,
        },
    )

    def __validateStore(self) -> None:
        """
        Validate and normalize the ``store`` property.

        Returns
        -------
        None
            Normalizes ``store`` to its canonical string value via
            ``object.__setattr__``.

        Raises
        ------
        TypeError
            If ``store`` is neither a ``Drivers`` enum nor a string.
        ValueError
            If ``store`` is a string that does not match any valid driver.
        """
        # Reject types that are neither Drivers enum nor string
        if not isinstance(self.store, (Drivers, str)):
            error_msg = (
                "The default job store must be an instance of "
                "Drivers or a string."
            )
            raise TypeError(error_msg)

        # Validate string driver names and normalise to canonical enum value
        if isinstance(self.store, str):
            _value = self.store.upper().strip()
            if _value not in _DRIVER_NAMES:
                error_msg = (
                    f"Invalid job store driver: {self.store}. "
                    f"Must be one of {sorted(_DRIVER_NAMES)!s}."
                )
                raise ValueError(error_msg)
            # Normalise to the canonical string value stored in the enum
            object.__setattr__(self, "store", Drivers[_value].value)
        else:
            # Extract the raw string value from the Drivers enum member
            object.__setattr__(self, "store", self.store.value)

    def __validateStores(self) -> None:
        """
        Validate and convert the ``stores`` property.

        Returns
        -------
        None
            Converts a ``dict`` to a ``Stores`` instance via
            ``object.__setattr__``.

        Raises
        ------
        TypeError
            If ``stores`` is not a ``Stores`` instance or a ``dict``.
        """
        # Reject stores that are neither Stores instances nor dicts
        if not isinstance(self.stores, (Stores, dict)):
            error_msg = (
                "The stores configuration must be an instance of "
                "Stores or a dictionary."
            )
            raise TypeError(error_msg)

        # Convert a plain dict to a typed Stores instance
        if isinstance(self.stores, dict):
            object.__setattr__(self, "stores", Stores(**self.stores))

    def __validateMaxInstances(self) -> None:
        """
        Validate the ``max_instances`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``max_instances`` is not an integer.
        ValueError
            If ``max_instances`` is lower than ``1``.
        """
        if not isinstance(self.max_instances, int) or isinstance(
            self.max_instances, bool,
        ):
            error_msg = "The 'max_instances' property must be an integer."
            raise TypeError(error_msg)
        if self.max_instances < 1:
            error_msg = "The 'max_instances' property must be at least 1."
            raise ValueError(error_msg)

    def __validateCoalesce(self) -> None:
        """
        Validate the ``coalesce`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``coalesce`` is not a boolean.
        """
        if not isinstance(self.coalesce, bool):
            error_msg = "The 'coalesce' property must be a boolean."
            raise TypeError(error_msg)

    def __validateMisfireGraceTime(self) -> None:
        """
        Validate the ``misfire_grace_time`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``misfire_grace_time`` is not an integer.
        ValueError
            If ``misfire_grace_time`` is negative.
        """
        if not isinstance(self.misfire_grace_time, int) or isinstance(
            self.misfire_grace_time, bool,
        ):
            error_msg = (
                "The 'misfire_grace_time' property must be an integer."
            )
            raise TypeError(error_msg)
        if self.misfire_grace_time < 0:
            error_msg = (
                "The 'misfire_grace_time' property cannot be negative."
            )
            raise ValueError(error_msg)

    def __validateReplaceExisting(self) -> None:
        """
        Validate the ``replace_existing`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``replace_existing`` is not a boolean.
        """
        if not isinstance(self.replace_existing, bool):
            error_msg = "The 'replace_existing' property must be a boolean."
            raise TypeError(error_msg)

    def __validateJitter(self) -> None:
        """
        Validate the ``jitter`` property.

        Returns
        -------
        None
            This method performs validation and returns None.

        Raises
        ------
        TypeError
            If ``jitter`` is not an integer.
        ValueError
            If ``jitter`` is negative.
        """
        if not isinstance(self.jitter, int) or isinstance(self.jitter, bool):
            error_msg = "The 'jitter' property must be an integer."
            raise TypeError(error_msg)
        if self.jitter < 0:
            error_msg = "The 'jitter' property cannot be negative."
            raise ValueError(error_msg)

    def __post_init__(self) -> None:
        """
        Validate and normalize the scheduler configuration after init.

        Returns
        -------
        None
            Modifies instance attributes in place via
            ``object.__setattr__``.

        Raises
        ------
        TypeError
            If any property does not match its expected type.
        ValueError
            If any property fails its value validation.
        """
        # Delegate base-class field validation
        super().__post_init__()

        # Validate each property according to its type hint
        self.__validateStore()
        self.__validateStores()
        self.__validateMaxInstances()
        self.__validateCoalesce()
        self.__validateMisfireGraceTime()
        self.__validateReplaceExisting()
        self.__validateJitter()
