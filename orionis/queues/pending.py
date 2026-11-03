"""Defer a single dispatch until awaited and allow options before submission."""

import asyncio
from typing import TYPE_CHECKING
from orionis.queues.exceptions import QueueDispatchError
from orionis.queues.functions import validate_name, validate_seconds

if TYPE_CHECKING:
    from collections.abc import Generator
    from orionis.queues.job import BaseJob
    from orionis.queues.types import DispatchCallback

class PendingDispatch:
    """Defer a single dispatch until awaited and allow options before submission."""

    __slots__ = (
        "_completion", "_connection", "_delay", "_job", "_queue", "_submit",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, submit: DispatchCallback, job: BaseJob) -> None:
        """
        Retain a job and its asynchronous submission callback.

        Parameters
        ----------
        submit : orionis.queues.types.DispatchCallback
            Manager entry point invoked only when awaited.
        job : orionis.queues.BaseJob
            Instance whose declared data will be serialized on submission.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._submit = submit
        """Manager entry point invoked only when awaited."""
        self._job: BaseJob | None = job
        """Instance whose declared data will be serialized on submission."""
        self._connection: str | None = None
        """Configured connection used to store or dispatch the operation."""
        self._queue: str | None = None
        """Name of the queue receiving or storing the job."""
        self._delay = 0.0
        """Delay value used by ``PendingDispatch``."""
        self._completion: asyncio.Future[str] | None = None
        """Completion provider or result associated with the primitive."""

    def onConnection(self, name: str) -> PendingDispatch:
        """
        Select the configured backend before submission.

        Parameters
        ----------
        name : str
            Connection name from queue configuration.

        Returns
        -------
        orionis.queues.PendingDispatch
            This pending operation.
        """
        self._checkMutable()
        self._connection = validate_name(name, "Connection")
        return self

    def onQueue(self, name: str) -> PendingDispatch:
        """
        Select a logical channel before submission.

        Parameters
        ----------
        name : str
            Channel within the selected connection.

        Returns
        -------
        orionis.queues.PendingDispatch
            This pending operation.
        """
        self._checkMutable()
        self._queue = validate_name(name, "Queue")
        return self

    def delay(self, seconds: float) -> PendingDispatch:
        """
        Schedule availability relative to submission time.

        Parameters
        ----------
        seconds : float
            Finite nonnegative delay.

        Returns
        -------
        orionis.queues.PendingDispatch
            This pending operation.
        """
        self._checkMutable()
        self._delay = validate_seconds(seconds, "Dispatch delay")
        return self

    def _checkMutable(self) -> None:
        """
        Reject changes after the submission task has started.

        Returns
        -------
        None
            Validate the pending operation's state.
        """
        if self._completion is not None:
            message = "An awaited dispatch cannot be modified."
            raise QueueDispatchError(message)

    async def _run(self) -> str:
        """
        Submit once and share the result with every awaiter.

        Returns
        -------
        str
            Persisted job identifier.
        """
        if self._completion is not None:
            return await asyncio.shield(self._completion)
        job = self._job
        if job is None:
            message = "The dispatch no longer contains a job."
            raise QueueDispatchError(message)
        completion = self._completion = asyncio.get_running_loop().create_future()
        self._job = None
        try:
            result = await self._submit(
                job, self._connection, self._queue, self._delay,
            )
        except asyncio.CancelledError:
            completion.cancel()
            raise
        except BaseException as error:
            completion.set_exception(error)
            completion.exception()
            raise
        else:
            completion.set_result(result)
            return result

    def __await__(self) -> Generator[object, None, str]:
        """
        Start or join the deferred dispatch when awaited.

        Returns
        -------
        collections.abc.Generator[object, None, str]
            Iterator consumed by Python's await protocol.
        """
        return self._run().__await__()
