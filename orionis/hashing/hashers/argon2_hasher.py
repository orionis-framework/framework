# ruff: noqa: ANN401, TC001
# Keep runtime injection types; resolve optional backend classes dynamically.
"""Hash passwords with Argon2id."""

import base64
from threading import Lock
from typing import Any, Self
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.execution import HASH_WORKERS
from orionis.hashing.hashers.functions import import_hasher_backend
from orionis.hashing.hashers.functions import ARGON2_MAX_COST as _MAX_COST
from orionis.hashing.hashers.functions import ARGON2_MAX_THREADS as _MAX_THREADS
from orionis.hashing.hashers.functions import (
    ARGON2_MEMORY_PER_THREAD as _MEMORY_PER_THREAD,
)

from orionis.support.concurrency import BoundedExecutor

# Backend location and distribution name reported when it is missing
_BACKEND_MODULE: str = "pwdlib.hashers.argon2"
"""Backend location and distribution name reported when it is missing."""
_BACKEND_CLASS: str = "Argon2Hasher"
"""Backend class identifier: ``Argon2Hasher``."""
_BACKEND_PACKAGE: str = "pwdlib[argon2]"
"""Backend package identifier: ``pwdlib[argon2]``."""

DEFAULT_MEMORY: int = 65536
"""Default per-operation memory cost in kibibytes."""
DEFAULT_THREADS: int = 4
"""Default number of parallel Argon2 lanes."""
DEFAULT_TIME: int = 3
"""Default number of passes over the allocated memory."""


class Argon2Hasher(IHasher):
    """Hash passwords with Argon2id.

    Use Argon2id as the framework's default password-hashing algorithm.

    Concurrency
    -----------
    A short lock protects parameter snapshots and cache publication. Backend
    construction and hashing run outside the lock. An operation already using
    previous parameters can finish after a setter, but cannot restore them
    in the shared cache.
    """

    __slots__ = (
        "_backend",
        "_backend_class",
        "_executor",
        "_memory",
        "_state_lock",
        "_threads",
        "_time",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self: Self,
        *,
        memory: int = DEFAULT_MEMORY,
        threads: int = DEFAULT_THREADS,
        time: int = DEFAULT_TIME,
        executor: BoundedExecutor | None = None,
    ) -> None:
        """
        Initialize the driver with its default cost parameters.

        Parameters
        ----------
        memory : int
            Memory cost in kibibytes, at least eight per lane and at most
            ``2**32 - 1``.
        threads : int
            Degree of parallelism from one through ``2**24 - 1``.
        time : int
            Number of iterations from one through ``2**32 - 1``.
        executor : orionis.support.concurrency.BoundedExecutor | None
            Caller-owned dedicated executor, or the shared bounded hashing pool.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If a cost exceeds native bounds or memory is insufficient per lane.
        """
        self._memory = self._validate("memory", memory)
        """Memory cost in kibibytes."""
        self._state_lock = Lock()
        """Lock protecting cost snapshots and backend cache publication."""
        self._executor = HASH_WORKERS if executor is None else executor
        """Caller-owned dedicated executor, or the shared bounded hashing pool."""
        self._threads = self._validate("threads", threads)
        """Degree of parallelism."""
        self._time = self._validate("time", time)
        """Number of iterations."""
        self._validateMemory(self._memory, self._threads)

        # The backend is imported and built on first use to keep the
        # driver constructible even when the dependency is absent.
        self._backend_class: Any = None
        """
        The backend is imported and built on first use to keep the driver
        constructible even when the dependency is absent.
        """
        self._backend: Any = None
        """Backend implementation used to perform the configured operation."""

    @staticmethod
    def _validate(name: str, value: int) -> int:
        """
        Ensure a cost parameter fits the native algorithm's integer range.

        Parameters
        ----------
        name : str
            Name of the parameter, used in the error message.
        value : int
            Value to validate.

        Returns
        -------
        int
            The validated value.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If the value is not a positive integer within the native range.
        """
        maximum = _MAX_THREADS if name == "threads" else _MAX_COST
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 1 <= value <= maximum
        ):
            error_msg = (
                f"The Argon2 '{name}' option must be an integer between "
                f"1 and {maximum}, got {value!r}."
            )
            raise HashConfigurationException(error_msg)
        return value

    @staticmethod
    def _validateMemory(memory: int, threads: int) -> None:
        """Require enough configured memory for every Argon2 lane.

        Parameters
        ----------
        memory : int
            Validated memory cost in kibibytes.
        threads : int
            Validated parallelism.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If fewer than eight kibibytes are available per lane.
        """
        if memory < _MEMORY_PER_THREAD * threads:
            error_msg = "Argon2 memory must be at least 8 KiB per thread."
            raise HashConfigurationException(error_msg)

    def _backendClass(self: Self) -> Any:
        """
        Return the backend class, importing it on first use.

        Returns
        -------
        typing.Any
            Backend class provided by the underlying library.

        Raises
        ------
        orionis.hashing.exceptions.MissingHashDependencyException
            If the backend package is not installed.
        """
        if self._backend_class is None:
            self._backend_class = import_hasher_backend(
                _BACKEND_MODULE,
                _BACKEND_CLASS,
                _BACKEND_PACKAGE,
            )
        return self._backend_class

    def _build(self: Self, memory: int, threads: int, time: int) -> Any:
        """
        Build a backend instance for the given cost parameters.

        Parameters
        ----------
        memory : int
            Memory cost in kibibytes.
        threads : int
            Degree of parallelism.
        time : int
            Number of iterations.

        Returns
        -------
        typing.Any
            Configured backend instance.
        """
        return self._backendClass()(
            time_cost=time,
            memory_cost=memory,
            parallelism=threads,
        )

    def _default(self: Self) -> Any:
        """
        Return the cached backend built from the configured parameters.

        Returns
        -------
        typing.Any
            Backend instance reused across calls.
        """
        with self._state_lock:
            if self._backend is not None:
                return self._backend
            parameters = self._memory, self._threads, self._time
        backend = self._build(*parameters)
        with self._state_lock:
            if parameters == (self._memory, self._threads, self._time):
                if self._backend is None:
                    self._backend = backend
                return self._backend
        return backend

    def _make(
        self: Self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str:
        """
        Hash a plain text value with Argon2id.

        Parameters
        ----------
        value : str
            Plain text value to hash.
        rounds : int | None
            Per-call time cost override.
        memory : int | None
            Per-call memory cost override, in kibibytes.
        threads : int | None
            Per-call parallelism override.

        Returns
        -------
        str
            Encoded Argon2id hash.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If an override exceeds native bounds or leaves insufficient memory
            for the selected parallelism.
        """
        # Reuse the cached backend unless the call overrides a cost value
        if rounds is None and memory is None and threads is None:
            backend = self._default()
        else:
            with self._state_lock:
                configured_memory = self._memory
                configured_threads = self._threads
                configured_time = self._time
            selected_memory = (
                configured_memory
                if memory is None
                else self._validate("memory", memory)
            )
            selected_threads = (
                configured_threads
                if threads is None
                else self._validate("threads", threads)
            )
            selected_time = (
                configured_time if rounds is None else self._validate("time", rounds)
            )
            self._validateMemory(selected_memory, selected_threads)
            backend = self._build(selected_memory, selected_threads, selected_time)

        return backend.hash(value)

    async def make(
        self: Self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str:
        """
        Hash a plain text value off the event loop.

        Parameters
        ----------
        value : str
            Plain text value to hash.
        rounds : int | None
            Per-call time cost override.
        memory : int | None
            Per-call memory cost override, in kibibytes.
        threads : int | None
            Per-call parallelism override.

        Returns
        -------
        str
            Encoded Argon2id hash.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If an override exceeds native bounds or leaves insufficient memory
            for the selected parallelism.
        """
        return await self._executor.run(
            self._make,
            value,
            rounds=rounds,
            memory=memory,
            threads=threads,
        )

    def _check(self: Self, value: str, hashed: str) -> bool:
        """
        Verify a plain text value against an Argon2id hash.

        Parameters
        ----------
        value : str
            Plain text value to verify.
        hashed : str
            Previously generated hash.

        Returns
        -------
        bool
            ``True`` when the value matches the hash, ``False`` otherwise.
        """
        # A hash produced by another algorithm can never match here
        if not hashed or not self._identify(hashed):
            return False
        return self._default().verify(value, hashed)

    async def check(self: Self, value: str, hashed: str) -> bool:
        """
        Verify a plain text value off the event loop.

        Parameters
        ----------
        value : str
            Plain text value to verify.
        hashed : str
            Previously generated hash.

        Returns
        -------
        bool
            ``True`` when the value matches the hash, ``False`` otherwise.
        """
        return await self._executor.run(self._check, value, hashed)

    def needsRehash(self: Self, hashed: str) -> bool:
        """
        Determine whether the hash uses outdated Argon2id parameters.

        Parameters
        ----------
        hashed : str
            Previously generated hash.

        Returns
        -------
        bool
            ``True`` when the hash should be regenerated.
        """
        # Hashes from another algorithm must always be regenerated
        if not hashed or not self._identify(hashed):
            return True
        backend = self._default()
        try:
            return backend.check_needs_rehash(hashed)
        except ValueError:
            return True

    def _identify(self: Self, hashed: str) -> bool:
        """
        Check whether the hash was produced by the Argon2 family.

        Parameters
        ----------
        hashed : str
            Hash to inspect.

        Returns
        -------
        bool
            ``True`` when the hash belongs to this driver.
        """
        if not self._backendClass().identify(hashed):
            return False
        try:
            encoded = hashed.decode("ascii") if isinstance(hashed, bytes) else hashed
            fields = encoded.rsplit("$", 2)
            for field in fields[-2:]:
                if not field or "=" in field:
                    return False
                decoded = base64.b64decode(
                    field + "=" * (-len(field) % 4),
                    validate=True,
                )
                if base64.b64encode(decoded).decode("ascii").rstrip("=") != field:
                    return False
        except ValueError:
            return False
        return True

    def getAlgorithm(self: Self) -> str:
        """
        Return the algorithm identifier of this driver.

        Returns
        -------
        str
            Always ``'argon2id'``.
        """
        return "argon2id"

    def setRounds(self: Self, rounds: int) -> Self:
        """
        Set the default time cost used by the driver.

        Parameters
        ----------
        rounds : int
            New number of iterations.

        Returns
        -------
        typing.Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If the value is outside the native time-cost range.
        """
        validated = self._validate("time", rounds)
        with self._state_lock:
            self._time = validated
            self._backend = None
        return self

    def setMemory(self: Self, memory: int) -> Self:
        """
        Set the default memory cost used by the driver.

        Parameters
        ----------
        memory : int
            New memory cost in kibibytes.

        Returns
        -------
        typing.Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If the value is outside the native memory range or insufficient
            for the configured parallelism.
        """
        validated = self._validate("memory", memory)
        with self._state_lock:
            self._validateMemory(validated, self._threads)
            self._memory = validated
            self._backend = None
        return self

    def setThreads(self: Self, threads: int) -> Self:
        """
        Set the default parallelism used by the driver.

        Parameters
        ----------
        threads : int
            New degree of parallelism.

        Returns
        -------
        typing.Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If the value is outside the native parallelism range or requires
            more memory than configured.
        """
        validated = self._validate("threads", threads)
        with self._state_lock:
            self._validateMemory(self._memory, validated)
            self._threads = validated
            self._backend = None
        return self
