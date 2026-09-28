from __future__ import annotations
import inspect
from typing import TYPE_CHECKING, Any
from orionis.orm.exceptions import OrmException
from orionis.orm.metaclass import MODEL_EVENTS

if TYPE_CHECKING:
    from collections.abc import Callable

# Events whose listeners can abort the operation by returning ``False``.
_HALTABLE_EVENTS: frozenset[str] = frozenset({
    "saving",
    "creating",
    "updating",
    "deleting",
    "restoring",
})

class EventsMixin:
    """
    Lifecycle event behavior shared by every model.

    Listeners are registered per model class and inherited by its
    subclasses. Listeners of the "before" events (``saving``,
    ``creating``, ``updating``, ``deleting``, ``restoring``) abort the
    operation by returning ``False``, mirroring Eloquent.
    """

    __slots__ = ()

    @classmethod
    def registerEvent(
        cls,
        event: str,
        listener: Callable[..., Any],
    ) -> type:
        """
        Register a listener for a model lifecycle event.

        Parameters
        ----------
        event : str
            Event name; one of the supported lifecycle events.
        listener : Callable
            Callable receiving the model instance. It may be a
            coroutine function and, for "before" events, returning
            ``False`` aborts the operation.

        Returns
        -------
        type
            The model class, enabling fluent chaining.

        Raises
        ------
        OrmException
            If the event name is not supported.
        """
        if event not in MODEL_EVENTS:
            supported = ", ".join(MODEL_EVENTS)
            error_msg = (
                f"Unsupported model event '{event}'. Supported events: "
                f"{supported}."
            )
            raise OrmException(error_msg)
        meta = cls.__meta__
        meta.events[event] = (*meta.events.get(event, ()), (object(), listener))
        return cls

    @classmethod
    def observe(cls, observer: Any) -> type:  # noqa: ANN401
        """
        Register every lifecycle method exposed by an observer.

        Parameters
        ----------
        observer : Any
            Object or class exposing methods named after the events it
            listens to.

        Returns
        -------
        type
            The model class, enabling fluent chaining.
        """
        target = observer() if isinstance(observer, type) else observer
        for event in MODEL_EVENTS:
            listener = getattr(target, event, None)
            if callable(listener):
                cls.registerEvent(event, listener)
        return cls

    @classmethod
    def flushEvents(cls, event: str | None = None) -> None:
        """
        Remove registered listeners from the model.

        Parameters
        ----------
        event : str or None, optional
            Event to clear, or ``None`` to clear every event.

        Returns
        -------
        None
            This method does not return a value.
        """
        meta = cls.__meta__
        if event is None:
            meta.events.clear()
        else:
            meta.events.pop(event, None)

    async def fireEvent(self, event: str) -> bool:
        """
        Dispatch a lifecycle event to its listeners.

        Parameters
        ----------
        event : str
            Event name being dispatched.

        Returns
        -------
        bool
            ``False`` when a listener of a haltable event vetoed the
            operation, ``True`` otherwise.
        """
        listeners = self.__meta__.events.get(event)
        if not listeners:
            return True

        haltable = event in _HALTABLE_EVENTS
        for _token, listener in listeners:
            result = listener(self)
            if inspect.isawaitable(result):
                result = await result
            if haltable and result is False:
                return False
        return True
