import threading

_MISSING: object = object()

class Singleton(type):
    """Create one instance per class with synchronous and asynchronous access."""

    def __init__(
        cls,
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
        bases : tuple[type, ...]
            Base classes of the class being initialized.
        namespace : dict[str, object]
            Attributes defined in the class body.
        """
        super().__init__(name, bases, namespace)
        type.__setattr__(cls, "_singleton_instance", _MISSING)
        type.__setattr__(cls, "_singleton_lock", threading.Lock())

    def __call__(
        cls,
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
        """
        instance = cls._singleton_instance
        if instance is not _MISSING:
            return instance

        with cls._singleton_lock:
            instance = cls._singleton_instance
            if instance is _MISSING:
                instance = super().__call__(*args, **kwargs)
                type.__setattr__(cls, "_singleton_instance", instance)

        return instance

    async def __acall__(
        cls,
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
        instance = cls._singleton_instance
        if instance is not _MISSING:
            return instance

        with cls._singleton_lock:
            instance = cls._singleton_instance
            if instance is _MISSING:
                instance = super().__call__(*args, **kwargs)
                type.__setattr__(cls, "_singleton_instance", instance)

        return instance
