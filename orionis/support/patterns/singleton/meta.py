"""Create one instance per class with synchronous and asynchronous access."""

import threading

_MISSING: object = object()
"""Sentinel distinguishing missing from ordinary values."""


class Singleton(type):
    """Create one instance per class with synchronous and asynchronous access."""

    def __init__(
        cls: type,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> None:
        """
        Initialize per-class singleton state with a sentinel and lock.

        Parameters
        ----------
        cls : type
            Class whose singleton state is initialized.
        name : str
            Name of the class being initialized.
        bases : tuple[type, ``...``]
            Base classes of the class being initialized.
        namespace : dict[str, object]
            Attributes defined in the class body.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init__(name, bases, namespace)
        type.__setattr__(cls, "_singleton_instance", _MISSING)
        type.__setattr__(cls, "_singleton_lock", threading.Lock())
        type.__setattr__(cls, "_singleton_owner", None)

    def __call__(
        cls: type,
        *args: object,
        **kwargs: object,
    ) -> object:
        """
        Create or retrieve the thread-safe singleton instance.

        Parameters
        ----------
        cls : type
            Class whose singleton instance is requested.
        *args : object
            Positional arguments passed to the class constructor on creation.
        **kwargs : object
            Keyword arguments passed to the class constructor on creation.

        Returns
        -------
        object
            The existing or newly created singleton instance.

        Raises
        ------
        RuntimeError
            If the constructor recursively requests the same singleton.
        """
        instance = cls._singleton_instance
        if instance is not _MISSING:
            return instance

        owner = threading.get_ident()
        if cls._singleton_owner == owner:
            error_msg = f"Recursive singleton construction for {cls.__name__}."
            raise RuntimeError(error_msg)

        with cls._singleton_lock:
            instance = cls._singleton_instance
            if instance is _MISSING:
                type.__setattr__(cls, "_singleton_owner", owner)
                try:
                    instance = super().__call__(*args, **kwargs)
                    type.__setattr__(cls, "_singleton_instance", instance)
                finally:
                    type.__setattr__(cls, "_singleton_owner", None)

        return instance

    async def __acall__(
        cls: type,
        *args: object,
        **kwargs: object,
    ) -> object:
        """
        Create or retrieve the singleton instance through an awaitable API.

        Parameters
        ----------
        cls : type
            Class whose singleton instance is requested.
        *args : object
            Positional arguments passed to the class constructor on creation.
        **kwargs : object
            Keyword arguments passed to the class constructor on creation.

        Returns
        -------
        object
            The existing or newly created singleton instance.
        """
        return Singleton.__call__(cls, *args, **kwargs)
