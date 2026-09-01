from typing import ClassVar
from orionis.console.output.console import Console
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.failure.entities.throwable import Throwable
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.default.responses import DefaultResponses
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.payload.body import PayloadTooLargeException
from orionis.http.request import Request
from orionis.http.request import UnsupportedMediaTypeException
from orionis.http.responses import Response
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.logging.contracts.logger import ILogger

# Mapping of specific exception types to their corresponding
# HTTP status codes and messages
_HTTP_STATUS_MAP: dict[type[BaseException], tuple[int, str]] = {
    RouteNotFound: (404, "Route not found"),
    MethodNotAllowed: (405, "Method not allowed"),
    PayloadTooLargeException: (413, "Payload too large"),
    UnsupportedMediaTypeException: (415, "Unsupported media type"),
    CSRFTokenMismatchException: (419, "CSRF token mismatch"),
}

class BaseExceptionHandler(IBaseExceptionHandler):

    # ruff: noqa: G004, TC001

    # Exceptions that should not be caught by the handler
    dont_catch: ClassVar[frozenset[type[BaseException]]] = frozenset()

    def __init__(
        self,
        default_responses: DefaultResponses,
    ) -> None:
        """
        Initialize the BaseExceptionHandler instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Default responses for HTTP error handling
        self.__default_responses = default_responses

    def toThrowable(
        self,
        exception: Exception,
    ) -> Throwable:
        """
        Convert an exception to a structured Throwable object.

        Parameters
        ----------
        exception : Exception
            Exception instance to be converted.

        Returns
        -------
        Throwable
            Structured Throwable object containing class, message, arguments,
            and traceback.
        """
        # Extract and stringify exception arguments
        args = exception.args or ("",)
        str_args = tuple(map(str, args))

        # Create and return the Throwable object
        return Throwable(
            classtype=type(exception),
            message=str_args[0],
            args=str_args,
            traceback=exception.__traceback__,
        )

    def isExceptionIgnored(
        self,
        exception: Exception,
    ) -> bool:
        """
        Determine whether the given exception should be ignored.

        Parameters
        ----------
        exception : Exception
            The exception instance to check.

        Returns
        -------
        bool
            True if the exception should be ignored, otherwise False.
        """
        # Ensure the input is an exception instance
        if not isinstance(exception, BaseException):
            error_msg = (
                f"Expected BaseException, got {type(exception).__name__}"
            )
            raise TypeError(error_msg)

        # O(1) frozenset membership test
        return type(exception) in self.dont_catch

    async def report(
        self,
        exception: Exception,
        log: ILogger,
    ) -> Throwable | None:
        """
        Report or log an exception.

        Parameters
        ----------
        exception : Exception
            The exception instance that was caught.
        log : ILogger
            The logger instance for error reporting.

        Returns
        -------
        Throwable or None
            The structured Throwable object if reported, otherwise None.
        """
        # Skip reporting if the exception should be ignored
        if self.isExceptionIgnored(exception):
            return None

        # Convert the exception into a structured Throwable object
        throwable = self.toThrowable(exception)

        # Log the exception details
        log.error(f"[{throwable.classtype.__name__}] {throwable.message}")

        # Return the structured exception
        return throwable

    async def handleCLI(
        self,
        exception: Exception,
        console: Console,
    ) -> None:
        """
        Render the exception message for CLI output.

        Parameters
        ----------
        exception : Exception
            The exception instance that was caught.
        console : IConsole
            The console instance for output.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Skip reporting if the exception should be ignored
        if self.isExceptionIgnored(exception):
            return

        # Output the exception details to the console
        console.exception(exception)

    async def handleHTTP(
        self,
        exception: Exception,
        request: Request | TransportAdapter,
    ) -> Response | None:
        """
        Handle the exception for HTTP responses.

        Parameters
        ----------
        exception : Exception
            The exception instance that was caught.
        request : Request | TransportAdapter
            The HTTP request instance or transport adapter that was being processed.

        Returns
        -------
        Response | None
            The HTTP response if handled, otherwise None.
        """
        # Skip reporting if the exception should be ignored
        if self.isExceptionIgnored(exception):
            return None

        # Resolve response format and exception type once
        wants_json = request.wantsJson()
        exc_type = type(exception)

        # Check if the exception type is in the predefined HTTP status map
        if exc_type in _HTTP_STATUS_MAP:
            status_code, content = _HTTP_STATUS_MAP[exc_type]
            return self.__default_responses.error(
                status_code=status_code,
                content=content,
                expects_json=wants_json,
            )

        # Handle 500 server error — resolve adapter type once
        is_adapter = isinstance(request, TransportAdapter)
        return self.__default_responses.exception(
            request_path=request.path() if is_adapter else request.path,
            request_method=request.method() if is_adapter else request.method,
            exception=exception,
            status_code=500,
        )
