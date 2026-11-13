# ruff: noqa: PLR0913, TC001
# Match the shared capture signature and expose its container annotation at runtime.
"""Adapt MCP failure observation without invoking protocol presentation."""

import asyncio
from orionis.container.contracts.container import IContainer
from orionis.failure.entities.context import FailureContext
from orionis.failure.runtime import FailureRuntime, capture
from orionis.foundation.contracts.application import IApplication


async def report(
    exception: BaseException,
    app: IContainer,
    *,
    transport: str = "in-process",
    phase: str = "execution",
    operation: str | None = None,
    correlation_id: str | int | None = None,
    expected: bool = False,
) -> None:
    """
    Observe an MCP failure without constructing a protocol response.

    Ignore task cancellation, keyboard interrupts, process exits, and generator
    closure. Application runtimes report only after activation; compatible
    embedding containers fall back to their unified exception handler.

    Parameters
    ----------
    exception : BaseException
        Failure to observe unless it is an ignored control-flow exception.
    app : orionis.container.contracts.container.IContainer
        Application or embedding container supplying the failure handler.
    transport : str, optional
        Transport name attached to failure metadata.
    phase : str, optional
        MCP lifecycle or execution phase associated with the failure.
    operation : str or None, optional
        Protocol method or operation name, when available.
    correlation_id : str | int | None, optional
        Request identifier converted to a string when present.
    expected : bool, optional
        Whether the failure is an expected protocol outcome.

    Returns
    -------
    None
        Finish available failure observation without encoding a protocol reply.
    """
    if isinstance(
        exception,
        (asyncio.CancelledError, KeyboardInterrupt, SystemExit, GeneratorExit),
    ):
        return
    receipt = await capture(
        exception,
        app=app,
        flow="mcp",
        phase=phase,
        operation=operation,
        correlation_id=None if correlation_id is None else str(correlation_id),
        expected=expected,
        metadata={"transport": transport},
    )
    if receipt is not None or isinstance(app, IApplication):
        return
    context = FailureContext(
        flow="mcp",
        phase=phase,
        operation=operation,
        correlation_id=None if correlation_id is None else str(correlation_id),
        expected=expected,
        metadata={"transport": transport},
    )
    if getattr(app, "getExceptionHandler", None) is not None:
        await FailureRuntime(app).dispatchFailure(exception, context=context)
