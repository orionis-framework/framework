from typing import TYPE_CHECKING
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.foundation.contracts.application import IApplication
from orionis.http.request import Request
from orionis.http.responses import Response

if TYPE_CHECKING:
    from orionis.failure.contracts.handler import IBaseExceptionHandler
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

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

    async def __getContext(self) -> KernelContext:
        """
        Retrieve the current kernel context from the application scope.

        Returns
        -------
        KernelContext
            The kernel type representing the current execution context.

        Raises
        ------
        RuntimeError
            If no active scope or kernel is found.
        """
        # Get the current application scope
        scope = self.__app.getCurrentScope()
        if scope is None:
            error_msg = "No active scope found for context retrieval."
            raise RuntimeError(error_msg)

        # Retrieve the kernel type from the scope
        kernel = await scope.get("kernel")
        if kernel is None:
            error_msg = "No kernel found in the current scope for context retrieval."
            raise RuntimeError(error_msg)

        # Return the kernel type as a string for context identification
        return kernel

    async def __ensureHandler(self) -> IBaseExceptionHandler:
        """
        Resolve and cache the exception handler from the application container.

        Returns
        -------
        IBaseExceptionHandler
            The resolved exception handler instance.
        """
        if self.__exception_handler is None:
            self.__exception_handler = await self.__app.getExceptionHandler()
        return self.__exception_handler

    async def exception(
        self,
        exception: BaseException | Exception,
        request: Request | TransportAdapter | None = None,
    ) -> Response | None:
        """
        Handle an exception based on the current kernel context.

        Parameters
        ----------
        exception : BaseException | Exception
            The exception instance to handle.
        request : Request | TransportAdapter | None, optional
            The HTTP request or transport adapter associated with the exception.

        Returns
        -------
        None | Response
            This method performs side effects and may return a Response.

        Notes
        -----
        Determines the context and delegates exception handling accordingly.
        """
        # Resolve handler and context once per call
        handler = await self.__ensureHandler()
        context = await self.__getContext()

        # Report the exception using the registered handler
        await self.__app.call(handler, "report", exception=exception)

        # Handle console exceptions without request context
        if context == KernelContext.CONSOLE:
            return await self.__app.call(
                handler,
                "handleCLI",
                exception=exception,
            )

        # Handle HTTP exceptions with the request context
        if context == KernelContext.HTTP:
            return await self.__app.call(
                handler,
                "handleHTTP",
                exception=exception,
                request=request,
            )

        # For other contexts, simply report the exception without handling
        return None
