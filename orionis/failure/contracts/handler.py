"""Define the contract for base exception handler implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.console.output.contracts.console import IConsole
    from orionis.failure.entities.throwable import Throwable
    from orionis.logging.contracts.logger import ILogger
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.request import Request
    from orionis.http.responses import Response

class IBaseExceptionHandler(ABC):
    """Define the contract for base exception handler implementations."""

    @abstractmethod
    def toThrowable(
        self,
        exception: BaseException,
    ) -> Throwable:
        """
        Convert an exception to a structured Throwable object.

        Parameters
        ----------
        exception : BaseException
            Exception instance to be converted.

        Returns
        -------
        orionis.failure.entities.Throwable
            Structured Throwable object containing class, message, arguments,
            and traceback.
        """

    @abstractmethod
    def isExceptionIgnored(
        self,
        exception: BaseException,
    ) -> bool:
        """
        Determine whether the given exception should be ignored.

        Parameters
        ----------
        exception : BaseException
            The exception instance to check.

        Returns
        -------
        bool
            True if the exception should be ignored, otherwise False.
        """

    @abstractmethod
    async def report(
        self,
        exception: BaseException,
        log: ILogger,
    ) -> Throwable | None:
        """
        Log an exception and its traceback as a single error record.

        Parameters
        ----------
        exception : BaseException
            The exception instance that was caught.
        log : orionis.logging.contracts.ILogger
            The logger instance for error reporting.

        Returns
        -------
        orionis.failure.entities.Throwable or None
            The structured Throwable object if reported, otherwise None.
        """

    @abstractmethod
    async def handleCLI(
        self,
        exception: BaseException,
        console: IConsole,
    ) -> None:
        """
        Render the exception message for CLI output.

        Parameters
        ----------
        exception : BaseException
            The exception instance that was caught.
        console : orionis.console.output.contracts.console.IConsole
            The console instance for output.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    async def handleHTTP(
        self,
        exception: BaseException,
        request: Request | TransportAdapter,
    ) -> Response | None:
        """
        Handle the exception for HTTP responses.

        Parameters
        ----------
        exception : BaseException
            The exception instance that was caught.
        request : Request | TransportAdapter
            The HTTP request instance or transport adapter that was being processed.

        Returns
        -------
        orionis.http.Response | None
            The HTTP response if handled, otherwise None.
        """
