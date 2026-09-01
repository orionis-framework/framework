from typing import Self
from orionis.foundation.config.hashing.entities.hashing import Hashing as _HashingConfig
from orionis.foundation.config.hashing.enums.drivers import Drivers
from orionis.foundation.contracts.application import IApplication
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashDriverNotSupportedException
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher

class HashManager(IHashManager):
    """Expose an algorithm-agnostic hashing API.

    Resolve the configured password hashing driver and delegate every
    operation to it, so application code never depends on a concrete
    algorithm.

    Concurrency
    -----------
    No locks are used. The only mutable state is the driver cache, written
    the first time a driver is resolved: a concurrent first resolution from
    several threads may build the same driver twice, and the last write
    wins. Every operation is synchronous and never suspends, so tasks
    sharing an event loop never observe a partially built cache.
    ``setRounds`` mutates the cached driver, and the provider binds this
    class as a singleton, so the change is visible to the whole
    application.
    """

    # ruff: noqa: TC001

    __slots__ = ("_config", "_default", "_drivers")

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the manager from the application hashing configuration.

        A missing ``hashing`` section falls back to the defaults declared by
        the configuration entity.

        Parameters
        ----------
        app : IApplication
            Application container used to read the configuration.

        Returns
        -------
        None
            This method initializes the instance and returns None.
        """
        config_data = app.config("hashing") or {}
        self._config: _HashingConfig = (
            _HashingConfig(**config_data)
            if isinstance(config_data, dict)
            else config_data
        )

        self._default: str = str(self._config.driver)
        self._drivers: dict[str, IHasher] = {}

    # ── Driver resolution ───────────────────────────────────────────────────

    def driver(self, name: str | None = None) -> IHasher:
        """
        Return the hasher bound to the named (or default) driver.

        Parameters
        ----------
        name : str | None
            Driver name (``'argon2'`` or ``'bcrypt'``). ``None`` selects
            the configured default driver.

        Returns
        -------
        IHasher
            Hasher instance for the requested driver, created on first
            access and cached afterwards.

        Raises
        ------
        HashDriverNotSupportedException
            If the requested driver is not supported.
        """
        resolved: str = name or self._default
        hasher = self._drivers.get(resolved)
        if hasher is None:
            hasher = self._build(resolved)
            self._drivers[resolved] = hasher
        return hasher

    def getDefaultDriver(self) -> str:
        """
        Return the name of the configured default driver.

        Returns
        -------
        str
            Driver name, such as ``'argon2'`` or ``'bcrypt'``.
        """
        return self._default

    def _build(self, name: str) -> IHasher:
        """
        Instantiate the driver identified by *name*.

        Parameters
        ----------
        name : str
            Driver name to build.

        Returns
        -------
        IHasher
            Configured hasher instance.

        Raises
        ------
        HashDriverNotSupportedException
            If *name* does not match any supported driver.
        """
        if name == Drivers.ARGON2.value:
            options = self._config.argon2
            return Argon2Hasher(
                memory=options.memory,
                threads=options.threads,
                time=options.time,
            )

        if name == Drivers.BCRYPT.value:
            return BcryptHasher(rounds=self._config.bcrypt.rounds)

        error_msg = (
            f"Unsupported hashing driver: '{name}'. "
            f"Must be one of {sorted(driver.value for driver in Drivers)!s}."
        )
        raise HashDriverNotSupportedException(error_msg)

    # ── Hashing API ─────────────────────────────────────────────────────────

    def make(
        self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str:
        """
        Hash a plain text value with the default driver.

        Parameters
        ----------
        value : str
            Plain text value to hash.
        rounds : int | None
            Per-call cost override.
        memory : int | None
            Per-call memory cost override, in kibibytes.
        threads : int | None
            Per-call parallelism override.

        Returns
        -------
        str
            Encoded hash produced by the default driver.
        """
        return self.driver().make(
            value,
            rounds=rounds,
            memory=memory,
            threads=threads,
        )

    def check(self, value: str, hashed: str) -> bool:
        """
        Verify a plain text value against an encoded hash.

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
        return self.driver().check(value, hashed)

    def needsRehash(self, hashed: str) -> bool:
        """
        Determine whether a hash was produced with outdated parameters.

        Parameters
        ----------
        hashed : str
            Previously generated hash.

        Returns
        -------
        bool
            ``True`` when the hash should be regenerated with the current
            configuration.
        """
        return self.driver().needsRehash(hashed)

    def getAlgorithm(self) -> str:
        """
        Return the algorithm identifier of the default driver.

        Returns
        -------
        str
            Algorithm identifier, such as ``'argon2id'`` or ``'bcrypt'``.
        """
        return self.driver().getAlgorithm()

    def setRounds(self, rounds: int) -> Self:
        """
        Set the default cost factor used by the default driver.

        Parameters
        ----------
        rounds : int
            New cost factor.

        Returns
        -------
        Self
            The same manager instance, allowing fluent configuration.

        Raises
        ------
        HashConfigurationException
            If the value is not valid for the active driver.
        """
        self.driver().setRounds(rounds)
        return self
