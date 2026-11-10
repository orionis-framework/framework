"""Resolve exception handling and reporting for application failures."""

from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.failure.entities.context import FailureContext, FailureReceipt
from orionis.failure.runtime import FailureRuntime, get_runtime, operation
from orionis.foundation.contracts.application import IApplication
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.request import Request
from orionis.http.responses import Response

class Catch(ICatch):

    # ruff: noqa: TC001
    """Resolve the unified handling plan and request native presentation."""

    def __init__(self, app: IApplication) -> None:
        """
        Initialize exception handling for the application.

        Parameters
        ----------
        app : orionis.foundation.contracts.application.IApplication
            Application used to locate the active failure runtime and scope.

        Returns
        -------
        None
            Store the application and defer standalone runtime creation.
        """
        self.__app: IApplication = app
        """The application instance used to resolve required services."""
        self.__standalone_runtime: FailureRuntime | None = None
        """Inactive coordinator for explicitly invoked standalone handling."""

    async def capture(
        self, exception: BaseException, *, context: FailureContext,
    ) -> FailureReceipt | None:
        """
        Observe an exception through the application's active failure runtime.

        Leave presentation to the execution owner; no active scope is required.

        Parameters
        ----------
        exception : BaseException
            Original exception instance to observe.
        context : orionis.failure.entities.context.FailureContext
            Immutable execution metadata for the failure.

        Returns
        -------
        orionis.failure.entities.context.FailureReceipt or None
            Delivery status, or ``None`` if no runtime is active or the exception
            represents cancellation or process control.
        """
        runtime = get_runtime(self.__app)
        if runtime is None:
            return None
        return await runtime.capture(exception, context=context)

    async def exception(
        self,
        exception: BaseException,
        request: Request | TransportAdapter | None = None,
    ) -> Response | None:
        """
        Handle an exception in the current kernel context.

        Resolve a handling plan through the active runtime or a standalone
        coordinator. Request presentation only for console and HTTP contexts.

        Parameters
        ----------
        exception : BaseException
            Original exception instance to handle.
        request : Request or TransportAdapter or None, optional
            HTTP request or transport adapter used for presentation, when available.

        Returns
        -------
        orionis.http.responses.Response or None
            Presentation result, or ``None`` when no handling plan is selected,
            the kernel is neither console nor HTTP, or no response is produced.

        Raises
        ------
        RuntimeError
            If the application has no active scope or kernel context.
        """
        app = self.__app
        runtime = get_runtime(app)
        scope = app.getCurrentScope()
        if scope is None:
            error_msg = "No active scope found for context retrieval."
            raise RuntimeError(error_msg)

        context = await scope.get("kernel")
        if context is None:
            error_msg = "No kernel found in the current scope for context retrieval."
            raise RuntimeError(error_msg)

        if context is KernelContext.CONSOLE:
            flow = "cli"
        elif context is KernelContext.HTTP:
            flow = "http"
        else:
            flow = "runtime"
        incident_context = FailureContext(flow=flow)
        # Reuse the operation's selected plan, including in-flight callback
        # delivery. Presentation must not invoke application policy or log again.
        with operation(app, flow=flow):
            if runtime is not None:
                handling = await runtime.handlingFor(
                    exception, context=incident_context,
                )
            else:
                # Preserve explicitly invoked standalone Catch behavior without
                # publishing an active application or observing bootstrap work.
                if self.__standalone_runtime is None:
                    self.__standalone_runtime = FailureRuntime(app)
                _, handling = await self.__standalone_runtime.dispatchFailure(
                    exception, context=incident_context,
                )
            if handling is None or context not in (
                KernelContext.CONSOLE, KernelContext.HTTP,
            ):
                return None
            return await handling.present(flow=flow, request=request)
