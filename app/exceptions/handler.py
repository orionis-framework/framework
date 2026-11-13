# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
from typing import ClassVar
from orionis.failure.base import BaseExceptionHandler
from orionis.failure.entities import FailureContext, FailureHandling


class ExceptionHandler(BaseExceptionHandler):
    """Select deferred logging and presentation for each application failure."""

    # Exceptions that should not be caught by the handler
    dont_catch: ClassVar[frozenset[type[BaseException]]] = frozenset()

    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling | None:
        """
        Receive runtime exceptions after successful application startup.

        Parameters
        ----------
        exception : BaseException
            Original exception, including expected failures.
        context : FailureContext
            Immutable origin, phase and correlation of the failure.

        Returns
        -------
        FailureHandling | None
            Incident plan whose logging and presentation the runtime executes.

        Notes
        -----
        Add shared application policy here and return the inherited plan to
        preserve default logging and responses. The runtime calls this hook
        once, completes logging, and leaves presentation to the protocol owner.
        Keep incident state local to avoid mixing concurrent operations.
        """
        return await super().handleFailure(exception, context)

    async def handleResult(
        self,
        value: object,
        context: FailureContext,
    ) -> FailureHandling | None:
        """
        Receive declared failed outcomes that did not raise an exception.

        Parameters
        ----------
        value : object
            Failed outcome supplied by its execution owner.
        context : FailureContext
            Immutable origin, phase and correlation of the outcome.

        Returns
        -------
        FailureHandling | None
            Optional incident plan; the base implementation returns None.

        Notes
        -----
        Add application policy here without manufacturing an exception or
        capturing the same outcome again. Return the inherited result so that
        later policy can supply a deferred plan without losing it.
        """
        return await super().handleResult(value, context)
