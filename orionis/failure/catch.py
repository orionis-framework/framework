import asyncio
from typing import TYPE_CHECKING
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.foundation.contracts.application import IApplication
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.request import Request
from orionis.http.responses import Response

if TYPE_CHECKING:
    from orionis.failure.contracts.handler import IBaseExceptionHandler

class Catch(ICatch):

    # ruff: noqa: TC001

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the Catch handler with the application instance.

        Parameters
        ----------
        app : IApplication
            The application instance used to resolve required services.

        Returns
        -------
        None
            This constructor does not return any value.
        """
        self.__app: IApplication = app
        self.__exception_handler: IBaseExceptionHandler | None = None
        self.__handler_lock = asyncio.Lock()

    async def exception(
        self,
        exception: BaseException,
        request: Request | TransportAdapter | None = None,
    ) -> Response | None:
        """
        Handle an exception based on the current kernel context.

        Parameters
        ----------
        exception : BaseException
            The exception instance to handle.
        request : Request | TransportAdapter | None, optional
            The HTTP request or transport adapter associated with the exception.

        Returns
        -------
        None | Response
            This method performs side effects and may return a Response.

        Raises
        ------
        RuntimeError
            If the application has no active scope or kernel context.

        Notes
        -----
        Determines the context and delegates exception handling accordingly.
        """
        app = self.__app
        handler = self.__exception_handler
        if handler is None:
            async with self.__handler_lock:
                handler = self.__exception_handler
                if handler is None:
                    handler = await app.getExceptionHandler()
                    self.__exception_handler = handler

        scope = app.getCurrentScope()
        if scope is None:
            error_msg = "No active scope found for context retrieval."
            raise RuntimeError(error_msg)

        context = await scope.get("kernel")
        if context is None:
            error_msg = "No kernel found in the current scope for context retrieval."
            raise RuntimeError(error_msg)

        # Report the exception using the registered handler
        await app.call(handler, "report", exception=exception)

        # Handle console exceptions without request context
        if context is KernelContext.CONSOLE:
            return await app.call(
                handler,
                "handleCLI",
                exception=exception,
            )

        # Handle HTTP exceptions with the request context
        if context is KernelContext.HTTP:
            return await app.call(
                handler,
                "handleHTTP",
                exception=exception,
                request=request,
            )

        # For other contexts, simply report the exception without handling
        return None
