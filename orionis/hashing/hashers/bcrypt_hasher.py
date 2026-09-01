from typing import Any, Self
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.functions import import_hasher_backend

# ruff: noqa: ANN401, ARG002

# Backend location and distribution name reported when it is missing
_BACKEND_MODULE: str = "pwdlib.hashers.bcrypt"
_BACKEND_CLASS: str = "BcryptHasher"
_BACKEND_PACKAGE: str = "pwdlib[bcrypt]"

# Bounds imposed by the bcrypt algorithm itself
MIN_ROUNDS: int = 4
MAX_ROUNDS: int = 31
DEFAULT_ROUNDS: int = 12

class BcryptHasher(IHasher):
    """Hash passwords with bcrypt.

    Kept for interoperability with existing applications that already
    store bcrypt hashes.

    Concurrency
    -----------
    No locks are used. The backend class and the backend instance are
    cached on first use: a concurrent first use from several threads may
    build them twice, and the last write wins. Hashing operations only read
    that cache, and the fluent setter drops it so later calls rebuild the
    backend with the new cost factor.
    """

    __slots__ = ("_backend", "_backend_class", "_rounds")

    def __init__(self, *, rounds: int = DEFAULT_ROUNDS) -> None:
        """
        Initialize the driver with its default cost factor.

        Parameters
        ----------
        rounds : int
            Cost factor, expressed as the base-2 logarithm of the
            iteration count.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        HashConfigurationException
            If ``rounds`` falls outside the range supported by bcrypt.
        """
        self._rounds = self._validate(rounds)

        # The backend is imported and built on first use to keep the
        # driver constructible even when the dependency is absent.
        self._backend_class: Any = None
        self._backend: Any = None

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
        HashConfigurationException
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

    def _backendClass(self) -> Any:
        """
        Return the backend class, importing it on first use.

        Returns
        -------
        Any
            Backend class provided by the underlying library.

        Raises
        ------
        MissingHashDependencyException
            If the backend package is not installed.
        """
        if self._backend_class is None:
            self._backend_class = import_hasher_backend(
                _BACKEND_MODULE,
                _BACKEND_CLASS,
                _BACKEND_PACKAGE,
            )
        return self._backend_class

    def _build(self, rounds: int) -> Any:
        """
        Build a backend instance for the given cost factor.

        Parameters
        ----------
        rounds : int
            Cost factor applied by the backend.

        Returns
        -------
        Any
            Configured backend instance.
        """
        return self._backendClass()(rounds=rounds)

    def _default(self) -> Any:
        """
        Return the cached backend built from the configured cost factor.

        Returns
        -------
        Any
            Backend instance reused across calls.
        """
        if self._backend is None:
            self._backend = self._build(self._rounds)
        return self._backend

    def make(
        self,
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
        HashConfigurationException
            If ``rounds`` falls outside the range supported by bcrypt.
        """
        # Reuse the cached backend unless the call overrides the cost
        backend = (
            self._default() if rounds is None else self._build(self._validate(rounds))
        )
        return backend.hash(value)

    def check(self, value: str, hashed: str) -> bool:
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
        return self._default().verify(value, hashed)

    def needsRehash(self, hashed: str) -> bool:
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

    def _identify(self, hashed: str) -> bool:
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
        return self._backendClass().identify(hashed)

    def getAlgorithm(self) -> str:
        """
        Return the algorithm identifier of this driver.

        Returns
        -------
        str
            Always ``'bcrypt'``.
        """
        return "bcrypt"

    def setRounds(self, rounds: int) -> Self:
        """
        Set the default cost factor used by the driver.

        Parameters
        ----------
        rounds : int
            New cost factor.

        Returns
        -------
        Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        HashConfigurationException
            If the value falls outside the range supported by bcrypt.
        """
        self._rounds = self._validate(rounds)

        # Drop the cached backend so the new cost takes effect
        self._backend = None
        return self
