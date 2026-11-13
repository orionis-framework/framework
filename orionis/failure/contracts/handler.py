# ruff: noqa: TC001
# Keep handler contract annotations available to dependency reflection.
"""Define the unified application failure handler contract."""

from __future__ import annotations
from abc import ABC, abstractmethod
from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling


class IBaseExceptionHandler(ABC):
    """Receive original failures and declared failed outcomes exactly once."""

    @abstractmethod
    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling | None:
        """
        Select deferred effects for the original exception.

        Defer logging to the runtime and presentation to the execution owner.

        Parameters
        ----------
        exception : BaseException
            Original exception instance supplied by the execution boundary.
        context : orionis.failure.entities.context.FailureContext
            Immutable execution metadata describing the failure.

        Returns
        -------
        orionis.failure.entities.handling.FailureHandling or None
            Deferred handling plan, or ``None`` to observe without logging or
            presentation.
        """

    @abstractmethod
    async def handleResult(
        self,
        value: object,
        context: FailureContext,
    ) -> FailureHandling | None:
        """
        Select deferred effects for a declared failed result.

        Preserve the original result without constructing an exception. Defer
        logging to the runtime and presentation to the execution owner.

        Parameters
        ----------
        value : object
            Original result classified as a failure by its execution owner.
        context : orionis.failure.entities.context.FailureContext
            Immutable execution metadata describing the failed result.

        Returns
        -------
        orionis.failure.entities.handling.FailureHandling or None
            Deferred handling plan, or ``None`` to observe without logging or
            presentation.
        """
