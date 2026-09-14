import asyncio
from typing import Any, TypeVar, Self, TYPE_CHECKING
from orionis.container.context.scope import ScopedContext

if TYPE_CHECKING:
    import types

T = TypeVar("T")

class ScopeManager:

    # ruff: noqa: ANN401

    __slots__ = ("__active", "__closed", "_instances", "_token")

    def __init__(self) -> None:
        """
        Initialize the ScopeManager.

        Initializes an empty dictionary to store scoped instances.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Dictionary to hold instances for the current scope
        self._instances: dict[object, object] = {}
        self.__active = False
        self.__closed = False

    @property
    def isActive(self) -> bool:
        """Report whether the owning scope is still open.

        Returns
        -------
        bool
            False before entry and after exit, including in child tasks
            retaining a reference to this scope.
        """
        return self.__active

    def __getitem__(self, key: object) -> object | None:
        """
        Retrieve the instance associated with the given key.

        Parameters
        ----------
        key : object
            The key identifying the instance.

        Returns
        -------
        object or None
            The instance associated with the key, or None if not present.
        """
        # Return the instance if present, else None
        return self._instances.get(key)

    def __setitem__(self, key: object, value: object) -> None:
        """
        Store an instance under the specified key.

        Parameters
        ----------
        key : object
            Key to associate with the instance.
        value : object
            Instance to store.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        RuntimeError
            If the scope has already closed.
        """
        # Store the instance in the internal dictionary
        if self.__closed:
            error_msg = "Cannot publish a service to a closed container scope."
            raise RuntimeError(error_msg)
        self._instances[key] = value

    def __contains__(self, key: object) -> bool:
        """
        Check whether the given key exists in the scope.

        Parameters
        ----------
        key : object
            The key to check for existence.

        Returns
        -------
        bool
            True if the key exists in the scope, otherwise False.
        """
        return key in self._instances

    def clear(self) -> None:
        """
        Remove all instances from the current scope.

        Clears the internal dictionary of all stored instances.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Clear all stored instances in the current scope
        self._instances.clear()

    async def __aenter__(self) -> Self:
        """
        Enter the asynchronous context and set the current scope.

        Sets the current scope in the ScopedContext to this instance.

        Returns
        -------
        Self
            The current ScopeManager instance.

        Raises
        ------
        RuntimeError
            If the scope is already active or has previously closed.
        """
        if self.__active or self.__closed:
            error_msg = "A container scope can only be entered once."
            raise RuntimeError(error_msg)
        self._token = ScopedContext.setCurrentScope(self)
        self.__active = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """
        Exit the asynchronous context and clear the current scope.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            The exception type, if any.
        exc_val : BaseException | None
            The exception value, if any.
        exc_tb : types.TracebackType | None
            The traceback object, if any.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Clear all stored instances and reset the current scope context
        self.__active = False
        self.__closed = True
        self.clear()
        ScopedContext.reset(self._token)

    async def get(self, key: object) -> Any | None:
        """
        Retrieve the instance associated with the given key asynchronously.

        Parameters
        ----------
        key : object
            The key identifying the instance.

        Returns
        -------
        Any or None
            The resolved instance associated with the key, or None if not found.
        """
        # Attempt to get the instance from the internal dictionary
        instance = self._instances.get(key)
        if instance is None:
            return None

        # If the instance is a coroutine, schedule it as a Task
        if asyncio.iscoroutine(instance):
            task = asyncio.create_task(instance)
            self._instances[key] = task
            instance = task

        # Await the Task if necessary and store the result
        if isinstance(instance, asyncio.Task):
            instance = await instance
            self[key] = instance

        # Return the resolved instance
        return instance

    def set(self, key: object, value: Any) -> None:
        """
        Store an instance in the scope.

        Parameters
        ----------
        key : object
            Key to associate with the instance.
        value : Any
            Instance to store, can be synchronous or a coroutine.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Store the instance (sync or coroutine) in the scope dictionary
        self[key] = value

    async def resolve(self, key: object) -> Any:
        """
        Resolve and return the instance for a given key.

        This method retrieves the instance associated with the provided key.
        Raises a KeyError if the instance is not found in the scope.

        Parameters
        ----------
        key : object
            The key identifying the instance.

        Returns
        -------
        Any
            The resolved instance associated with the key.

        Raises
        ------
        KeyError
            If the instance for the given key is not found in the scope.
        """
        instance = await self.get(key)
        if instance is None:
            error_msg = (
                f"Instance for key {key!r} not found in scope"
            )
            raise KeyError(error_msg)
        return instance
