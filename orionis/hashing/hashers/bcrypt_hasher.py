# ruff: noqa: ANN401, ARG002, TC001
# Keep runtime injection types; dynamic backends share an interface with Argon2 costs.
"""Hash passwords with bcrypt."""

import re
from threading import Lock
from typing import Any, Self
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.execution import HASH_WORKERS
from orionis.hashing.hashers.functions import import_hasher_backend

from orionis.support.concurrency import BoundedExecutor

# Backend location and distribution name reported when it is missing
_BACKEND_MODULE: str = "pwdlib.hashers.bcrypt"
"""Backend location and distribution name reported when it is missing."""
_BACKEND_CLASS: str = "BcryptHasher"
"""Backend class identifier: ``BcryptHasher``."""
_BACKEND_PACKAGE: str = "pwdlib[bcrypt]"
"""Backend package identifier: ``pwdlib[bcrypt]``."""

# Bounds imposed by the bcrypt algorithm itself
MIN_ROUNDS: int = 4
"""Minimum accepted base-two logarithm of the bcrypt iteration count."""
MAX_ROUNDS: int = 31
"""Maximum accepted base-two logarithm of the bcrypt iteration count."""
DEFAULT_ROUNDS: int = 12
"""Default base-two logarithm of the bcrypt iteration count."""

_HASH_PATTERN = re.compile(
    r"\$2[abxy]\$(?:0[4-9]|[12][0-9]|3[01])\$"
    r"[./A-Za-z0-9]{21}[.Oeu][./A-Za-z0-9]{30}[.CGKOSWaeimquy26]",
)
"""Canonical bcrypt cost, salt, and digest encoding without unused trailing bits."""


class BcryptHasher(IHasher):
    """Hash passwords with bcrypt.

    Kept for interoperability with existing applications that already
    store bcrypt hashes.

    Concurrency
    -----------
    A short lock protects parameter snapshots and cache publication. Backend
    construction and hashing run outside the lock. An operation already using
    the previous cost can finish after a setter, but cannot restore that cost
    in the shared cache.
    """

    __slots__ = ("_backend", "_backend_class", "_executor", "_rounds", "_state_lock")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self: Self,
        *,
        rounds: int = DEFAULT_ROUNDS,
        executor: BoundedExecutor | None = None,
    ) -> None:
        """
        Initialize the driver with its default cost factor.

        Parameters
        ----------
        rounds : int
            Cost factor, expressed as the base-2 logarithm of the
            iteration count.
        executor : orionis.support.concurrency.BoundedExecutor | None
            Caller-owned dedicated executor, or the shared bounded hashing pool.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If ``rounds`` falls outside the range supported by bcrypt.
        """
        self._rounds = self._validate(rounds)
        """Cost factor, expressed as the base-2 logarithm of the iteration count."""
        self._state_lock = Lock()
        """Lock protecting cost snapshots and backend cache publication."""
        self._executor = HASH_WORKERS if executor is None else executor
        """Caller-owned dedicated executor, or the shared bounded hashing pool."""

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
    def _validate(rounds: int) -> int:
        """
        Ensure the cost factor is supported by bcrypt.

        Parameters
        ----------
        rounds : int
            Value to validate.

        Returns
        -------
        int
            The validated value.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If the value is not an integer within the supported range.
        """
        if (
            not isinstance(rounds, int)
            or isinstance(rounds, bool)
            or not MIN_ROUNDS <= rounds <= MAX_ROUNDS
        ):
            error_msg = (
                f"The bcrypt 'rounds' option must be an integer between "
                f"{MIN_ROUNDS} and {MAX_ROUNDS}, got {rounds!r}."
            )
            raise HashConfigurationException(error_msg)
        return rounds

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

    def _build(self: Self, rounds: int) -> Any:
        """
        Build a backend instance for the given cost factor.

        Parameters
        ----------
        rounds : int
            Cost factor applied by the backend.

        Returns
        -------
        typing.Any
            Configured backend instance.
        """
        return self._backendClass()(rounds=rounds)

    def _default(self: Self) -> Any:
        """
        Return the cached backend built from the configured cost factor.

        Returns
        -------
        typing.Any
            Backend instance reused across calls.
        """
        with self._state_lock:
            if self._backend is not None:
                return self._backend
            rounds = self._rounds
        backend = self._build(rounds)
        with self._state_lock:
            if rounds == self._rounds:
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
        Hash a plain text value with bcrypt.

        Parameters
        ----------
        value : str
            Plain text value to hash.
        rounds : int | None
            Per-call cost factor override.
        memory : int | None
            Ignored, bcrypt has no memory cost parameter.
        threads : int | None
            Ignored, bcrypt has no parallelism parameter.

        Returns
        -------
        str
            Encoded bcrypt hash.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If ``rounds`` falls outside the range supported by bcrypt.
        """
        # Reuse the cached backend unless the call overrides the cost
        backend = (
            self._default() if rounds is None else self._build(self._validate(rounds))
        )
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
            Per-call cost factor override.
        memory : int | None
            Ignored, bcrypt has no memory cost parameter.
        threads : int | None
            Ignored, bcrypt has no parallelism parameter.

        Returns
        -------
        str
            Encoded bcrypt hash.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If ``rounds`` falls outside the range supported by bcrypt.
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
        Verify a plain text value against a bcrypt hash.

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
        backend = self._default()
        try:
            return backend.verify(value, hashed)
        except ValueError:
            return False

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
        Determine whether the hash uses an outdated cost factor.

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
        return self._default().check_needs_rehash(hashed)

    def _identify(self: Self, hashed: str) -> bool:
        """
        Check whether the hash was produced by bcrypt.

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
        encoded = hashed.decode("ascii") if isinstance(hashed, bytes) else hashed
        return _HASH_PATTERN.fullmatch(encoded) is not None

    def getAlgorithm(self: Self) -> str:
        """
        Return the algorithm identifier of this driver.

        Returns
        -------
        str
            Always ``'bcrypt'``.
        """
        return "bcrypt"

    def setRounds(self: Self, rounds: int) -> Self:
        """
        Set the default cost factor used by the driver.

        Parameters
        ----------
        rounds : int
            New cost factor.

        Returns
        -------
        typing.Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        orionis.hashing.exceptions.HashConfigurationException
            If the value falls outside the range supported by bcrypt.
        """
        validated = self._validate(rounds)
        with self._state_lock:
            self._rounds = validated
            self._backend = None
        return self
