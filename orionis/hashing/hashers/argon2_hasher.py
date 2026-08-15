from typing import Any, Self
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.functions import import_hasher_backend

# ruff: noqa: ANN401

# Backend location and distribution name reported when it is missing
_BACKEND_MODULE: str = "pwdlib.hashers.argon2"
_BACKEND_CLASS: str = "Argon2Hasher"
_BACKEND_PACKAGE: str = "pwdlib[argon2]"

# Default cost parameters recommended for interactive logins
DEFAULT_MEMORY: int = 65536
DEFAULT_THREADS: int = 4
DEFAULT_TIME: int = 3

class Argon2Hasher(IHasher):
    """Hash passwords with Argon2id.

    Argon2id won the Password Hashing Competition and is the recommended
    default driver of the framework.
    """

    __slots__ = ("_backend", "_backend_class", "_memory", "_threads", "_time")

    def __init__(
        self,
        *,
        memory: int = DEFAULT_MEMORY,
        threads: int = DEFAULT_THREADS,
        time: int = DEFAULT_TIME,
    ) -> None:
        """
        Initialize the driver with its default cost parameters.

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
        None
            This method initializes the instance and returns None.

        Raises
        ------
        HashConfigurationException
            If any cost parameter is not a positive integer.
        """
        self._memory = self._validate("memory", memory)
        self._threads = self._validate("threads", threads)
        self._time = self._validate("time", time)

        # The backend is imported and built on first use to keep the
        # driver constructible even when the dependency is absent.
        self._backend_class: Any = None
        self._backend: Any = None

    @staticmethod
    def _validate(name: str, value: int) -> int:
        """
        Ensure a cost parameter is a strictly positive integer.

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
        HashConfigurationException
            If the value is not an integer greater than zero.
        """
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            error_msg = (
                f"The Argon2 '{name}' option must be an integer greater "
                f"than zero, got {value!r}."
            )
            raise HashConfigurationException(error_msg)
        return value

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

    def _build(self, memory: int, threads: int, time: int) -> Any:
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
        Any
            Configured backend instance.
        """
        return self._backendClass()(
            time_cost=time,
            memory_cost=memory,
            parallelism=threads,
        )

    def _default(self) -> Any:
        """
        Return the cached backend built from the configured parameters.

        Returns
        -------
        Any
            Backend instance reused across calls.
        """
        if self._backend is None:
            self._backend = self._build(self._memory, self._threads, self._time)
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
        HashConfigurationException
            If any override is not a positive integer.
        """
        # Reuse the cached backend unless the call overrides a cost value
        if rounds is None and memory is None and threads is None:
            backend = self._default()
        else:
            backend = self._build(
                self._memory if memory is None else self._validate("memory", memory),
                self._threads
                if threads is None
                else self._validate("threads", threads),
                self._time if rounds is None else self._validate("time", rounds),
            )

        return backend.hash(value)

    def check(self, value: str, hashed: str) -> bool:
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

    def needsRehash(self, hashed: str) -> bool:
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
        return self._default().check_needs_rehash(hashed)

    def _identify(self, hashed: str) -> bool:
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
        return self._backendClass().identify(hashed)

    def getAlgorithm(self) -> str:
        """
        Return the algorithm identifier of this driver.

        Returns
        -------
        str
            Always ``'argon2id'``.
        """
        return "argon2id"

    def setRounds(self, rounds: int) -> Self:
        """
        Set the default time cost used by the driver.

        Parameters
        ----------
        rounds : int
            New number of iterations.

        Returns
        -------
        Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        HashConfigurationException
            If the value is not a positive integer.
        """
        self._time = self._validate("time", rounds)

        # Drop the cached backend so the new cost takes effect
        self._backend = None
        return self

    def setMemory(self, memory: int) -> Self:
        """
        Set the default memory cost used by the driver.

        Parameters
        ----------
        memory : int
            New memory cost in kibibytes.

        Returns
        -------
        Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        HashConfigurationException
            If the value is not a positive integer.
        """
        self._memory = self._validate("memory", memory)
        self._backend = None
        return self

    def setThreads(self, threads: int) -> Self:
        """
        Set the default parallelism used by the driver.

        Parameters
        ----------
        threads : int
            New degree of parallelism.

        Returns
        -------
        Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        HashConfigurationException
            If the value is not a positive integer.
        """
        self._threads = self._validate("threads", threads)
        self._backend = None
        return self
