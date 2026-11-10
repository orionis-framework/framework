"""
Observe failures only inside an activated application runtime.

This module deliberately depends only on the standard library and failure
entities. Protocols keep ownership of responses, cancellation and recovery.
"""

# Keyword context fields keep allocations on the error path. Helpers in this
# module cooperate with the private ledger and pending-report registry.
# ruff: noqa: PLR0913, SLF001

from __future__ import annotations
import asyncio
import contextvars
import sys
from dataclasses import replace
from contextlib import contextmanager
from concurrent.futures import Future as ThreadFuture
from threading import Lock
from typing import TYPE_CHECKING, Self
from uuid import uuid4
from orionis.failure.entities.context import FailureContext, FailureReceipt
from orionis.failure.entities.handling import FailureHandling

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from concurrent.futures import Future

_current: contextvars.ContextVar[_Operation | None] = contextvars.ContextVar(
    "orionis_failure_operation",
    default=None,
)
_reporting: contextvars.ContextVar[FailureRuntime | None] = contextvars.ContextVar(
    "orionis_failure_reporting",
    default=None,
)

def _emergency(
    exception: BaseException | None,
    context: FailureContext,
    secondary: BaseException | None = None,
) -> None:
    """
    Write fallback diagnostics without exposing exception messages.

    Parameters
    ----------
    exception : BaseException or None
        Failure whose type is reported, or ``None`` for a failed result.
    context : FailureContext
        Incident metadata supplying the event identifier.
    secondary : BaseException or None, optional
        Reporting failure whose type is included in the diagnostic.

    Returns
    -------
    None
        Emit a minimal stderr diagnostic and suppress ordinary write errors.
    """
    try:
        primary_name = type(exception).__name__ if exception is not None else "result"
        secondary_name = (
            type(secondary).__name__ if secondary is not None else "unavailable"
        )
        # Messages and tracebacks may contain credentials; retain the original
        # object for the caller and avoid exposing it through emergency stderr.
        sys.stderr.write(
            f"Orionis failure {context.event_id}: {primary_name}; "
            f"reporting unavailable ({secondary_name}).\n",
        )
    except Exception:  # noqa: BLE001, S110 - Last resort must not recurse.
        pass

def _find_runtime(app: object | None = None) -> FailureRuntime | None:
    """
    Find an owned runtime without resolving a global facade.

    Parameters
    ----------
    app : object or None, optional
        Application to inspect; use the current operation only when ``None``.

    Returns
    -------
    FailureRuntime or None
        Runtime attached to the application or current operation, regardless of
        activation state, or ``None`` if unavailable.
    """
    if app is not None:
        runtime = getattr(app, "_failure_runtime", None)
        return runtime if isinstance(runtime, FailureRuntime) else None
    current = _current.get()
    return current.runtime if current is not None else None

def get_runtime(app: object | None = None) -> FailureRuntime | None:
    """
    Return the active runtime for an application or current operation.

    Parameters
    ----------
    app : object or None, optional
        Application to inspect; use the current operation only when ``None``.

    Returns
    -------
    FailureRuntime or None
        Resolved runtime if active, otherwise ``None``.
    """
    runtime = _find_runtime(app)
    return runtime if runtime is not None and runtime.active else None

@contextmanager
def _handler_dependencies() -> Generator[None]:
    """
    Detach request and operation scopes while resolving shared handlers.

    Yields
    ------
    None
        Enter a scope-free context and restore the previous contexts on exit.
    """
    from orionis.container.context.scope import (  # noqa: PLC0415
        reset_scope,
        set_current_scope,
    )

    token = set_current_scope(None)
    failure_token = _current.set(None)
    try:
        yield
    finally:
        _current.reset(failure_token)
        reset_scope(token)

class _Incident:
    """Keep deferred effects and their completion inside an operation ledger."""

    __slots__ = (
        "abandoned", "context", "exception", "handling", "ready", "receipt", "started",
    )

    def __init__(self, exception: BaseException, receipt: FailureReceipt) -> None:
        """
        Initialize an incident with its original exception and delivery status.

        Parameters
        ----------
        exception : BaseException
            Original exception retained for identity-based lookup.
        receipt : FailureReceipt
            Initial delivery status for the incident.

        Returns
        -------
        None
            Store the failure and prepare an unresolved completion signal.
        """
        self.exception = exception
        self.receipt = receipt
        self.context: FailureContext | None = None
        self.handling: FailureHandling | None = None
        self.ready: ThreadFuture = ThreadFuture()
        self.started = False
        self.abandoned = False

    def abandon(self) -> None:
        """
        Mark unstarted delivery as abandoned and notify waiting owners.

        Returns
        -------
        None
            Degrade the receipt and finish the incident only if delivery has not
            started.
        """
        if not self.started:
            self.abandoned = True
            self.receipt = replace(self.receipt, degraded=True)
            self.finish(None)

    def reclaim(self) -> None:
        """
        Reset an abandoned incident for another delivery attempt.

        Returns
        -------
        None
            Preserve the event identifier and replace receipt and completion state.
        """
        self.abandoned = False
        self.receipt = FailureReceipt(event_id=self.receipt.event_id)
        self.ready = ThreadFuture()

    def finish(self, handling: FailureHandling | None) -> None:
        """
        Store the selected handling plan and notify incident waiters.

        Parameters
        ----------
        handling : FailureHandling or None
            Deferred handling plan, or ``None`` when no plan is available.

        Returns
        -------
        None
            Set the plan and resolve the completion signal if it is still pending.
        """
        self.handling = handling
        if not self.ready.done():
            self.ready.set_result(None)

    async def wait(self) -> None:
        """
        Await incident completion without cancelling its delivery.

        Use a loop-local notification so cancelling one waiter leaves the shared
        completion signal intact.

        Returns
        -------
        None
            Resume after the incident's completion signal is resolved.

        Raises
        ------
        asyncio.CancelledError
            If this waiter is cancelled.
        """
        loop = asyncio.get_running_loop()
        while not self.ready.done():
            notification = loop.create_future()

            def wake(signal: asyncio.Future = notification) -> None:
                """
                Resolve the current waiter's loop-local notification.

                Parameters
                ----------
                signal : asyncio.Future, optional
                    Notification future captured for this wait iteration.

                Returns
                -------
                None
                    Set the signal result to ``None`` unless it is already done.
                """
                if not signal.done():
                    signal.set_result(None)

            def finished(_future: ThreadFuture, callback: object = wake) -> None:
                """
                Enqueue a wake-up callback on the waiter's event loop.

                Parameters
                ----------
                _future : concurrent.futures.Future
                    Completed incident signal; its value is unused.
                callback : object, optional
                    Wake-up callback captured for this wait iteration.

                Returns
                -------
                None
                    Schedule the callback unless the loop can no longer accept it.
                """
                try:
                    loop.call_soon_threadsafe(callback)
                except RuntimeError:
                    # A cancelled waiter may already have closed its event loop.
                    return

            self.ready.add_done_callback(finished)
            await notification

class _Operation:
    """Own an error-only ledger for one execution and its nested boundaries."""

    __slots__ = (
        "closed",
        "correlation_id",
        "flow",
        "ledger",
        "name",
        "owns",
        "parent",
        "runtime",
        "token",
    )

    def __init__(
        self,
        runtime: FailureRuntime | None,
        flow: str,
        name: str | None,
        correlation_id: str | None,
        *,
        isolated: bool,
        parent: _Operation | None,
    ) -> None:
        """
        Initialize operation metadata and select its ledger owner.

        Parameters
        ----------
        runtime : FailureRuntime or None
            Runtime associated with this execution, if available.
        flow : str
            Execution-flow label.
        name : str or None
            Logical operation name.
        correlation_id : str or None
            Correlation identifier supplied by the execution owner.
        isolated : bool
            Own a separate ledger even when a compatible parent exists.
        parent : _Operation or None
            Enclosing operation; ignore closed parents or a different runtime.

        Returns
        -------
        None
            Store execution metadata and defer ledger allocation until an incident.
        """
        self.runtime = runtime
        self.flow = flow
        self.name = name
        self.correlation_id = correlation_id
        self.parent = (
            parent if parent is not None and not parent.closed
            and parent.runtime is runtime else None
        )
        self.owns = isolated or self.parent is None
        self.ledger: dict[int, _Incident] | None = None
        self.token = None
        self.closed = False

    def __enter__(self) -> Self:
        """
        Bind this operation to the current context.

        Returns
        -------
        typing.Self
            This operation, with the previous context retained for restoration.
        """
        self.token = _current.set(self)
        return self

    def _owner(self) -> _Operation:
        """
        Return the nearest operation that owns the shared incident ledger.

        Returns
        -------
        _Operation
            This operation or its nearest ledger-owning ancestor.
        """
        current = self
        while not current.owns and current.parent is not None:
            current = current.parent
        return current

    def incident(self, error: BaseException) -> _Incident | None:
        """
        Find the recorded incident for an exception by object identity.

        Parameters
        ----------
        error : BaseException
            Original exception to locate in the owner ledger.

        Returns
        -------
        _Incident or None
            Matching incident from a live owner ledger, or ``None`` if absent.
        """
        if self.closed:
            return None
        owner = self._owner()
        ledger = owner.ledger if not owner.closed else None
        if ledger is None:
            return None
        found = ledger.get(id(error))
        return found if found is not None and found.exception is error else None

    def lookup(self, error: BaseException) -> FailureReceipt | None:
        """
        Find a receipt for an exception or an entirely observed group.

        Parameters
        ----------
        error : BaseException
            Exception or exception group whose observation status is needed.

        Returns
        -------
        FailureReceipt or None
            Direct receipt, or the first child receipt when every group member
            has been observed; ``None`` otherwise.
        """
        found = self.incident(error)
        if found is not None:
            return found.receipt
        if isinstance(error, BaseExceptionGroup):
            receipts = [self.lookup(child) for child in error.exceptions]
            if receipts and all(receipts):
                return receipts[0]
        return None

    def adopt(self, incident: _Incident) -> None:
        """
        Add an incident to the live ledger owner.

        Parameters
        ----------
        incident : _Incident
            Delivery record to retain by original exception identity.

        Returns
        -------
        None
            Record the incident unless this operation or its owner has closed.
        """
        if self.closed:
            return
        owner = self._owner()
        if owner.closed:
            return
        if owner.ledger is None:
            owner.ledger = {}
        owner.ledger[id(incident.exception)] = incident

    def _propagate(self, error: BaseException) -> None:
        """
        Transfer escaping incidents to the parent operation.

        Parameters
        ----------
        error : BaseException
            Exception or exception group leaving the owned operation.

        Returns
        -------
        None
            Transfer matching incidents when a parent and owned ledger exist.
        """
        if self.parent is None or not self.ledger:
            return
        pending = [error]
        while pending:
            candidate = pending.pop()
            if isinstance(candidate, BaseExceptionGroup):
                pending.extend(candidate.exceptions)
            found = self.ledger.get(id(candidate))
            if found is not None and found.exception is candidate:
                self.parent.adopt(found)

    def __exit__(
        self, exc_type: object, error: BaseException | None, traceback: object,
    ) -> None:
        """
        Restore the parent context and release this operation's ledger.

        Parameters
        ----------
        exc_type : object
            Exception type supplied by the context manager protocol; unused.
        error : BaseException or None
            Exception leaving the block, if any.
        traceback : object
            Traceback supplied by the context manager protocol; unused.

        Returns
        -------
        None
            Propagate escaping incident records and close without suppressing
            the exception.
        """
        # Explicitly transfer incident identity when a nested operation raises
        # back to its parent; independent attempts keep independent ledgers.
        if error is not None and self.owns:
            self._propagate(error)
        if self.token is not None:
            _current.reset(self.token)
        self.closed = True
        if self.owns and self.ledger is not None:
            self.ledger.clear()

class _InactiveOperation:
    """Allocation-free context when no application observation is active."""

    __slots__ = ()
    closed = True
    ledger = None
    runtime = None

    def __enter__(self) -> Self:
        """
        Enter the shared no-op operation context.

        Returns
        -------
        typing.Self
            This inactive singleton without allocating execution state.
        """
        return self

    def __exit__(self, *_args: object) -> None:
        """
        Leave the inactive context without suppressing exceptions.

        Parameters
        ----------
        *_args : object
            Unused exception details supplied by the context manager protocol.

        Returns
        -------
        None
            Leave observation state unchanged and do not suppress exceptions.
        """
        return # NOSONAR

_inactive_operation = _InactiveOperation()

class _BorrowedOperation:
    """Reuse identical nested metadata without replacing or closing its owner."""

    __slots__ = ()

    def __enter__(self) -> _Operation:
        """
        Return the operation already bound to the current context.

        Returns
        -------
        _Operation
            Existing operation reused without taking ownership of its lifetime.
        """
        return _current.get()

    def __exit__(self, *_args: object) -> None:
        """
        Leave the borrowed context without closing its owner.

        Parameters
        ----------
        *_args : object
            Unused exception details supplied by the context manager protocol.

        Returns
        -------
        None
            Preserve the owning operation and do not suppress exceptions.
        """
        return # NOSONAR

_borrowed_operation = _BorrowedOperation()

def operation(
    app: object | None = None,
    *,
    runtime: FailureRuntime | None = None,
    flow: str = "runtime",
    operation: str | None = None,
    correlation_id: str | None = None,
    isolated: bool = False,
) -> _Operation | _InactiveOperation | _BorrowedOperation:
    """
    Bind or reuse an execution context for failure observation.

    Allocate a ledger only when an incident is observed. Never capture or
    suppress exceptions; callers must report before consuming a failure.

    Parameters
    ----------
    app : object or None, optional
        Application owning the runtime; use the current operation when omitted.
    runtime : FailureRuntime or None, optional
        Explicit runtime taking precedence over application-based resolution.
    flow : str, optional
        Execution-flow label. Defaults to ``"runtime"``.
    operation : str or None, optional
        Logical operation name, if known.
    correlation_id : str or None, optional
        Correlation identifier shared by related incidents, if supplied.
    isolated : bool, default False
        Own a separate incident ledger instead of sharing the parent ledger.

    Returns
    -------
    _Operation or _InactiveOperation or _BorrowedOperation
        Owned or borrowed context manager, or a no-op context if observation
        is inactive.
    """
    if isinstance(runtime, FailureRuntime):
        runtime = runtime if runtime.active else None
    else:
        runtime = get_runtime(app)
    current = _current.get()
    if runtime is None and (current is None or current.runtime is None):
        return _inactive_operation
    if (
        not isolated and current is not None and not current.closed
        and current.runtime is runtime and current.flow == flow
        and current.name == operation and current.correlation_id == correlation_id
    ):
        return _borrowed_operation
    return _Operation(
        runtime, flow, operation, correlation_id, isolated=isolated, parent=current,
    )

def current_operation() -> _Operation | None:
    """
    Return the live operation bound to the current context.

    Returns
    -------
    _Operation or None
        Current operation, or ``None`` when no live operation is bound.
    """
    current = _current.get()
    return current if current is not None and not current.closed else None

def _runtime_operation(runtime: FailureRuntime) -> _Operation | None:
    """
    Return the live operation only when it belongs to the supplied runtime.

    Parameters
    ----------
    runtime : FailureRuntime
        Runtime whose current operation is required.

    Returns
    -------
    _Operation or None
        Live operation associated with this runtime, or ``None``.
    """
    current = current_operation()
    return current if current is not None and current.runtime is runtime else None

def _previous_receipt(
    exception: BaseException, current: _Operation | None, incident: _Incident | None,
) -> FailureReceipt | None:
    """
    Reuse a direct incident receipt or an already observed group's receipt.

    Parameters
    ----------
    exception : BaseException
        Exception or exception group to look up.
    current : _Operation or None
        Operation supplying the ledger when no direct incident is available.
    incident : _Incident or None
        Previously located incident, if any.

    Returns
    -------
    FailureReceipt or None
        Existing incident or ledger receipt, or ``None`` when neither is available.
    """
    if incident is not None:
        return incident.receipt
    return current.lookup(exception) if current is not None else None

def _parent_context(
    exception: BaseException, context: FailureContext, current: _Operation | None,
) -> FailureContext:
    """
    Link a secondary failure to an already observed cause.

    Parameters
    ----------
    exception : BaseException
        Failure whose explicit cause or implicit context may have been observed.
    context : FailureContext
        Metadata to enrich when no parent event is already set.
    current : _Operation or None
        Operation used to look up the causal failure.

    Returns
    -------
    FailureContext
        Context with the cause's event identifier, or the original context when
        no link can be added.
    """
    if current is None or context.parent_event_id is not None:
        return context
    cause = exception.__cause__ or exception.__context__
    parent = current.lookup(cause) if cause is not None else None
    if parent is not None:
        return replace(context, parent_event_id=parent.event_id)
    return context

def handoff(
    exception: BaseException,
    *,
    target: _Operation | None,
    receipt: FailureReceipt | None = None,
) -> bool:
    """
    Transfer an observed incident to its awaiting operation owner.

    Reuse incident identity instead of mutating the exception.

    Parameters
    ----------
    exception : BaseException
        Original exception whose delivery record is being transferred.
    target : _Operation or None
        Destination operation; reject unavailable or closed targets.
    receipt : FailureReceipt or None, optional
        Known receipt; otherwise look up the receipt in the current operation.

    Returns
    -------
    bool
        ``True`` when a receipt can be handed to the live, compatible target,
        otherwise ``False``.
    """
    if target is None or target.closed:
        return False
    source = current_operation()
    if source is not None and source.runtime is not target.runtime:
        return False
    if receipt is None and source is not None:
        receipt = source.lookup(exception)
    if receipt is None:
        return False
    incident = source.incident(exception) if source is not None else None
    if incident is not None:
        target.adopt(incident)
    else:
        incident = _Incident(exception, receipt)
        incident.started = True
        incident.finish(None)
        target.adopt(incident)
    return True

class FailureRuntime:
    """Own one application's handler, active lifetimes and pending reports."""

    def __init__(
        self, app: object, handler: object | None = None, *, timeout: float = 5.0,
    ) -> None:
        """
        Initialize runtime ownership, reporting state, and task registries.

        Parameters
        ----------
        app : object
            Application providing handler resolution, construction, and invocation.
        handler : object or None, optional
            Pre-resolved failure handler; resolve lazily when omitted.
        timeout : float, optional
            Maximum seconds allowed for each handler or logging action. Defaults
            to ``5.0``.

        Returns
        -------
        None
            Store configuration without activating observation.
        """
        self.app = app
        self.handler = handler
        self.timeout = timeout
        self._owners: set[object] = set()
        self._closing_owners: set[object] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending: set[asyncio.Task] = set()
        self._tasks: set[asyncio.Task] = set()
        self._thread_pending: set[Future] = set()
        self._pending_lock = Lock()
        self._prepare_lock = asyncio.Lock()
        self.lifecycle_lock = asyncio.Lock()
        self._reporting_enabled = True
        self._fallback_handler = None

    @property
    def active(self) -> bool:
        """
        Check whether active or closing owners keep observation enabled.

        Returns
        -------
        bool
            ``True`` if either ownership set is nonempty, otherwise ``False``.
        """
        return bool(self._owners or self._closing_owners)

    @property
    def ownerCount(self) -> int:
        """
        Return the number of owners still holding resource ownership.

        Returns
        -------
        int
            Count of active owners, excluding owners already moved into closing.
        """
        return len(self._owners)

    def hasOwner(self, owner: object) -> bool:
        """
        Check whether an owner is active or still completing shutdown.

        Parameters
        ----------
        owner : object
            Hashable lifecycle token to locate in the ownership sets.

        Returns
        -------
        bool
            ``True`` if the owner appears in either ownership set, otherwise
            ``False``.
        """
        return owner in self._owners or owner in self._closing_owners

    async def prepare(self) -> None:
        """
        Resolve the application handler once outside operational scopes.

        Returns
        -------
        None
            Cache the handler while serializing concurrent resolution attempts.
        """
        if self.handler is not None:
            return
        async with self._prepare_lock:
            if self.handler is not None:
                return
            with _handler_dependencies():
                self.handler = await self.app.getExceptionHandler()

    def activate(self, owner: object) -> None:
        """
        Register a started owner and record the current event loop.

        Parameters
        ----------
        owner : object
            Hashable lifecycle token whose startup completed.

        Returns
        -------
        None
            Enable reporting for a newly registered owner and retain its event loop.

        Raises
        ------
        RuntimeError
            If no event loop is running in the current thread.
        """
        if owner not in self._owners:
            self._reporting_enabled = True
        self._loop = asyncio.get_running_loop()
        self._owners.add(owner)

    async def start(self, owner: object) -> None:
        """
        Activate an owner after earlier lifecycle transitions complete.

        Parameters
        ----------
        owner : object
            Hashable token for the successfully started lifecycle.

        Returns
        -------
        None
            Register the owner while holding the runtime lifecycle lock.
        """
        async with self.lifecycle_lock:
            self.activate(owner)

    def deactivate(self, owner: object) -> None:
        """
        Release active and closing ownership for a lifecycle token.

        Parameters
        ----------
        owner : object
            Hashable lifecycle token whose work and reporting have drained.

        Returns
        -------
        None
            Remove the token from both ownership sets without affecting other owners.
        """
        self._owners.discard(owner)
        self._closing_owners.discard(owner)

    def beginClosing(self, owner: object) -> None:
        """
        Move an owner into closing while retaining cleanup observation.

        Call while holding ``lifecycle_lock``; drain reports before deactivation.

        Parameters
        ----------
        owner : object
            Hashable lifecycle token retiring its resource ownership.

        Returns
        -------
        None
            Move an active owner to the closing set; leave other tokens unchanged.
        """
        if owner in self._owners:
            self._owners.remove(owner)
            self._closing_owners.add(owner)

    def stopReporting(self) -> None:
        """
        Disable logging effects while retaining owner-based observation.

        Returns
        -------
        None
            Leave activation unchanged and suppress subsequent logging actions.
        """
        self._reporting_enabled = False

    async def _invoke(self, method: str, **kwargs: object) -> object:
        """
        Invoke an application handler method within the reporting timeout.

        Parameters
        ----------
        method : str
            Name of the configured failure-handler method to invoke.
        **kwargs : object
            Keyword arguments passed through application dependency injection.

        Returns
        -------
        object
            Value returned by the selected handler method.

        Raises
        ------
        TimeoutError
            If handler preparation or invocation exceeds the configured timeout.
        """
        async with asyncio.timeout(self.timeout):
            if self.handler is None:
                await self.prepare()
            return await self.app.call(self.handler, method, **kwargs)

    async def _attempt(
        self,
        method: str,
        original: BaseException | None,
        incident: FailureContext,
        **kwargs: object,
    ) -> tuple[bool, FailureHandling | None]:
        """
        Select and validate deferred effects through an application hook.

        Parameters
        ----------
        method : str
            Application failure-handler method to invoke.
        original : BaseException or None
            Original exception for fallback diagnostics, or ``None`` for a result.
        incident : FailureContext
            Incident metadata used if application policy fails.
        **kwargs : object
            Keyword arguments forwarded to the application hook.

        Returns
        -------
        tuple[bool, FailureHandling | None]
            Whether policy completed with a valid return value, plus its plan.
            Return ``(False, None)`` after recoverable hook failures.

        Raises
        ------
        BaseException
            If caller cancellation or another control-flow exception must propagate.
        """
        try:
            handling = await self._invoke(method, **kwargs)
            if handling is not None and not isinstance(handling, FailureHandling):
                message = "Failure handlers must return FailureHandling or None."
                raise TypeError(message)
        except BaseException as secondary:
            if isinstance(secondary, asyncio.CancelledError):
                task = asyncio.current_task()
                if task is not None and task.cancelling():
                    raise
            elif not isinstance(secondary, Exception):
                raise
            _emergency(original, incident, secondary)
            return False, None
        return True, handling

    async def _defaultHandling(
        self, exception: BaseException, context: FailureContext,
    ) -> FailureHandling | None:
        """
        Select native failure effects after application policy fails.

        Parameters
        ----------
        exception : BaseException
            Original failure to pass to the native exception handler.
        context : FailureContext
            Incident metadata controlling the fallback policy.

        Returns
        -------
        FailureHandling or None
            Native handling plan, or ``None`` when no plan can be selected.

        Raises
        ------
        BaseException
            If caller cancellation or another control-flow exception must propagate.
        """
        from orionis.failure.base.handler import BaseExceptionHandler  # noqa: PLC0415
        try:
            async with asyncio.timeout(self.timeout):
                handler = self.handler
                if not isinstance(handler, BaseExceptionHandler):
                    if self._fallback_handler is None:
                        with _handler_dependencies():
                            self._fallback_handler = await self.app.build(
                                BaseExceptionHandler,
                            )
                    handler = self._fallback_handler
                return await BaseExceptionHandler.handleFailure(
                    handler, exception, context,
                )
        except BaseException as secondary:
            if isinstance(secondary, asyncio.CancelledError):
                task = asyncio.current_task()
                if task is not None and task.cancelling():
                    raise
            elif not isinstance(secondary, Exception):
                raise
            _emergency(exception, context, secondary)
            return None

    def _correlate(self, context: FailureContext) -> FailureContext:
        """
        Assign operation correlation lazily when recording a failure.

        Parameters
        ----------
        context : FailureContext
            Metadata to correlate with the current operation for this runtime.

        Returns
        -------
        FailureContext
            Context carrying an existing or newly allocated correlation identifier,
            or the original context when correlation is already set or unavailable.
        """
        current = current_operation()
        if (
            context.correlation_id is None
            and current is not None
            and current.runtime is self
        ):
            owner = current._owner()
            if owner.correlation_id is None:
                owner.correlation_id = uuid4().hex
            return replace(
                context, correlation_id=current.correlation_id or owner.correlation_id,
            )
        return context

    def _begin(
        self, exception: BaseException, *, context: FailureContext,
        claimed: _Incident | None = None,
    ) -> tuple[FailureContext, FailureReceipt, _Incident | None]:
        """
        Claim or reuse an incident before handler execution can suspend.

        Parameters
        ----------
        exception : BaseException
            Original exception whose incident identity is being claimed.
        context : FailureContext
            Metadata supplied for the observation attempt.
        claimed : _Incident or None, optional
            Callback incident already claimed before asynchronous delivery.

        Returns
        -------
        tuple[FailureContext, FailureReceipt, _Incident | None]
            Resolved context, delivery receipt, and incident. A duplicate receipt
            signals that the caller must not deliver the failure again.
        """
        with self._pending_lock:
            current = _runtime_operation(self)
            incident = claimed or (
                current.incident(exception) if current is not None else None
            )
            if incident is not None and incident.abandoned:
                if claimed is not None:
                    return context, replace(incident.receipt, duplicate=True), incident
                context = incident.context or context
                incident.reclaim()
                context = replace(context, event_id=incident.receipt.event_id)
            previous = _previous_receipt(exception, current, incident)
            if previous is not None and (
                previous.event_id != context.event_id
                or (incident is not None and incident.started)
            ):
                return context, replace(previous, duplicate=True), incident
            return self._recordIncident(exception, context, current, incident)

    def _recordIncident(
        self, exception: BaseException, context: FailureContext,
        current: _Operation | None, incident: _Incident | None,
    ) -> tuple[FailureContext, FailureReceipt, _Incident]:
        """
        Record a new or reclaimed incident before invoking a handler.

        Parameters
        ----------
        exception : BaseException
            Original exception to retain in the incident.
        context : FailureContext
            Metadata to enrich with event, correlation, and parent identifiers.
        current : _Operation or None
            Current operation that can retain the incident.
        incident : _Incident or None
            Reclaimed incident, or ``None`` to create one.

        Returns
        -------
        tuple[FailureContext, FailureReceipt, _Incident]
            Enriched context, fresh receipt, and incident marked as started.
        """
        if not self._reporting_enabled and context.reporting_allowed:
            context = replace(context, reporting_allowed=False)
        if context.event_id is None:
            context = replace(context, event_id=uuid4().hex)
        context = self._correlate(context)
        context = _parent_context(exception, context, current)
        receipt = FailureReceipt(event_id=context.event_id)
        # Claim before awaiting: sibling callbacks for the same operation must
        # not enter the reporter twice. The ledger is scoped, never global.
        if incident is None:
            incident = _Incident(exception, receipt)
            if current is not None:
                current.adopt(incident)
        incident.receipt = receipt
        incident.started = True
        incident.context = context
        return context, receipt, incident

    async def _completeHandling(
        self, handling: FailureHandling | None, exception: BaseException | None,
        context: FailureContext,
    ) -> tuple[bool, bool]:
        """
        Complete selected logging effects without requesting presentation.

        Parameters
        ----------
        handling : FailureHandling or None
            Deferred plan to complete, or ``None`` for observation without effects.
        exception : BaseException or None
            Original failure, or ``None`` for a failed result.
        context : FailureContext
            Metadata controlling whether reporting is allowed or expected.

        Returns
        -------
        tuple[bool, bool]
            Reported and degraded status flags, respectively.

        Raises
        ------
        BaseException
            If caller cancellation or another control-flow exception must propagate.
        """
        if not self._reporting_enabled or not context.reporting_allowed:
            if not context.expected:
                _emergency(exception, context)
            return False, True
        if handling is None:
            return False, False
        try:
            async with asyncio.timeout(self.timeout):
                await handling.complete()
        except BaseException as secondary:
            if isinstance(secondary, asyncio.CancelledError):
                task = asyncio.current_task()
                if task is not None and task.cancelling():
                    raise
            elif not isinstance(secondary, Exception):
                raise
            handling.degraded = True
            _emergency(exception, context, secondary)
        return handling.reported, handling.degraded

    async def capture(
        self, exception: BaseException, *, context: FailureContext,
        _incident: _Incident | None = None,
    ) -> FailureReceipt | None:
        """
        Observe an original exception once per operation.

        Leave presentation to the execution owner and ignore cancellation or
        process-control exceptions.

        Parameters
        ----------
        exception : BaseException
            Original exception instance to observe.
        context : FailureContext
            Execution metadata for the incident.
        _incident : _Incident or None, optional
            Incident claimed by a callback before asynchronous delivery.

        Returns
        -------
        FailureReceipt or None
            Delivery receipt, including duplicate status, or ``None`` when inactive
            or when the exception represents cancellation or process control.

        Raises
        ------
        BaseException
            If delivery is interrupted by caller cancellation or a control-flow
            failure in the reporting path.
        """
        if not self.active:
            if _incident is not None:
                _incident.abandon()
            return None
        if isinstance(
            exception,
            (asyncio.CancelledError, KeyboardInterrupt, SystemExit, GeneratorExit),
        ):
            if _incident is not None:
                _incident.abandon()
            return None
        context, receipt, incident = self._begin(
            exception, context=context, claimed=_incident,
        )
        if receipt.duplicate:
            return receipt
        handling = None
        try:
            receipt, handling = await self.dispatchFailure(exception, context=context)
        except BaseException:
            receipt = replace(receipt, degraded=True)
            raise
        finally:
            incident.receipt = receipt
            incident.finish(handling)
        return receipt

    async def dispatchFailure(
        self, exception: BaseException, *, context: FailureContext,
    ) -> tuple[FailureReceipt, FailureHandling | None]:
        """
        Select and complete failure effects without requesting presentation.

        Allow explicitly invoked standalone handling without activating the
        runtime; normal framework observation enters through ``capture``.

        Parameters
        ----------
        exception : BaseException
            Original exception supplied to application policy.
        context : FailureContext
            Incident metadata, with an event identifier allocated if needed.

        Returns
        -------
        tuple[FailureReceipt, FailureHandling | None]
            Delivery and logging status, followed by the selected plan, if any.

        Raises
        ------
        BaseException
            If cancellation or a control-flow error escapes application policy.
        """
        if context.event_id is None:
            context = replace(context, event_id=uuid4().hex)
        receipt = FailureReceipt(event_id=context.event_id)
        reporter = _reporting.get()
        if reporter is not None and reporter.app is self.app:
            _emergency(exception, context)
            return replace(receipt, degraded=True), None
        token = _reporting.set(self)
        degraded = False
        reported = False
        delivered = False
        handling = None
        try:
            delivered, handling = await self._attempt(
                "handleFailure", exception, context,
                exception=exception, context=context,
            )
            if not delivered:
                degraded = True
                handling = await self._defaultHandling(exception, context)
            reported, effects_failed = await self._completeHandling(
                handling, exception, context,
            )
            degraded = degraded or effects_failed
        except Exception as secondary:  # noqa: BLE001 - Preserve the original.
            degraded = True
            _emergency(exception, context, secondary)
        finally:
            _reporting.reset(token)
        return replace(
            receipt, delivered=delivered, reported=reported, degraded=degraded,
        ), handling

    async def handlingFor(
        self, exception: BaseException, *, context: FailureContext,
    ) -> FailureHandling | None:
        """
        Return the selected plan without observing the exception twice.

        Wait for in-flight delivery and retry claims abandoned before execution.

        Parameters
        ----------
        exception : BaseException
            Original exception whose deferred handling is required.
        context : FailureContext
            Metadata for observation or native fallback selection.

        Returns
        -------
        FailureHandling or None
            Shared plan, or ``None`` when observation is inactive, reporting is
            recursive, or no plan is selected.
        """
        if not self.active or _reporting.get() is self:
            return None
        with operation(runtime=self, flow=context.flow):
            while True:
                receipt = await self.capture(exception, context=context)
                if receipt is None:
                    return None
                current = current_operation()
                incident = current.incident(exception) if current is not None else None
                if incident is None:
                    break
                await incident.wait()
                if incident.abandoned:
                    continue
                if incident.context is None:
                    break
                return incident.handling
            return await self._fallbackPresentation(
                exception, context, receipt, current, incident,
            )

    async def _fallbackPresentation(
        self, exception: BaseException, context: FailureContext,
        receipt: FailureReceipt, current: _Operation | None, incident: _Incident | None,
    ) -> FailureHandling | None:
        """
        Share native presentation planning for an incident without a plan.

        Parameters
        ----------
        exception : BaseException
            Previously observed exception requiring presentation policy.
        context : FailureContext
            Metadata passed to fallback policy with reporting disabled.
        receipt : FailureReceipt
            Existing delivery status used for the fallback claim.
        current : _Operation or None
            Operation that can retain the fallback incident.
        incident : _Incident or None
            Existing incident, or ``None`` to create a shared fallback claim.

        Returns
        -------
        FailureHandling or None
            Native handling plan, or ``None`` when fallback selection yields no plan.
        """
        if incident is None:
            incident = _Incident(exception, receipt)
            if current is not None:
                current.adopt(incident)
        else:
            incident.ready = ThreadFuture()
        incident.started = True
        incident.context = context
        handling = None
        try:
            handling = await self._defaultHandling(
                exception, replace(context, reporting_allowed=False),
            )
        finally:
            incident.finish(handling)
        return handling

    async def captureResult(
        self, value: object, *, context: FailureContext,
    ) -> FailureReceipt | None:
        """
        Observe a declared failed result without constructing an exception.

        Parameters
        ----------
        value : object
            Original result classified as a failure by its execution owner.
        context : FailureContext
            Execution metadata for the failed result.

        Returns
        -------
        FailureReceipt or None
            Delivery and reporting status, or ``None`` when the runtime is inactive.

        Raises
        ------
        BaseException
            If cancellation or a control-flow error escapes application policy.
        """
        if not self.active:
            return None
        if context.event_id is None:
            context = replace(context, event_id=uuid4().hex)
        if not self._reporting_enabled and context.reporting_allowed:
            context = replace(context, reporting_allowed=False)
        context = self._correlate(context)
        receipt = FailureReceipt(event_id=context.event_id)
        if _reporting.get() is self:
            _emergency(None, context)
            return replace(receipt, degraded=True)
        token = _reporting.set(self)
        try:
            delivered, handling = await self._attempt(
                "handleResult", None, context, value=value, context=context,
            )
            reported, degraded = await self._completeHandling(handling, None, context)
            return replace(
                receipt, delivered=delivered, reported=reported,
                degraded=not delivered or degraded,
            )
        except Exception as secondary:  # noqa: BLE001 - Preserve the outcome.
            _emergency(None, context, secondary)
            return replace(receipt, degraded=True)
        finally:
            _reporting.reset(token)

    async def drain(self) -> None:
        """
        Await owned callback reports until no pending report remains.

        Include reports enqueued during draining. Return immediately from this
        runtime's application reporter to avoid self-deadlock.

        Returns
        -------
        None
            Wait for loop-side and cross-thread report registries to empty.
        """
        # A hook cannot join itself (including its cross-thread submission),
        # or a parent task awaiting that hook. Its external owner does the drain.
        if _reporting.get() is self:
            return
        while True:
            with self._pending_lock:
                thread_pending = tuple(self._thread_pending)
            pending = (
                *tuple(self._pending),
                *(asyncio.wrap_future(future) for future in thread_pending),
            )
            if not pending:
                return
            await asyncio.gather(*pending, return_exceptions=True)

    def createTask(
        self, coroutine: object, *, name: str | None = None,
    ) -> asyncio.Task:
        """
        Create and supervise application work until shutdown.

        Parameters
        ----------
        coroutine : object
            Awaitable application work whose failures must be observed.
        name : str or None, optional
            Task name and operation label for failure observation.

        Returns
        -------
        asyncio.Task
            Supervised task registered for cancellation during runtime shutdown.

        Raises
        ------
        RuntimeError
            If no event loop is running.
        """

        async def run() -> object:
            """
            Await application work inside an isolated background operation.

            Returns
            -------
            object
                Result returned by the supervised awaitable.

            Raises
            ------
            BaseException
                If the work fails or is cancelled, after attempted observation.
            """
            with operation(
                runtime=self, flow="background", operation=name, isolated=True,
            ):
                try:
                    return await coroutine
                except BaseException as error:
                    await capture(
                        error, runtime=self, flow="background", operation=name,
                    )
                    raise

        task = asyncio.create_task(run(), name=name)
        self._tasks.add(task)

        def finished(completed: asyncio.Task) -> None:
            """
            Release a completed application task and collect its outcome.

            Parameters
            ----------
            completed : asyncio.Task
                Owned task that finished or was cancelled.

            Returns
            -------
            None
                Remove task ownership, close the coroutine after cancellation
                when possible, and retrieve unhandled exceptions.
            """
            self._tasks.discard(completed)
            if completed.cancelled():
                # Cancellation before first execution never entered run().
                if hasattr(coroutine, "close"):
                    coroutine.close()
            else:
                completed.exception()

        task.add_done_callback(finished)
        return task

    async def shutdown(self) -> None:
        """
        Cancel owned application tasks and drain their failure reports.

        Exclude the current task and return immediately from a reporting callback
        to avoid waiting on the reporter itself.

        Returns
        -------
        None
            Await task cleanup and all pending callback reports.
        """
        if _reporting.get() is self:
            return
        tasks = tuple(
            task for task in self._tasks if task is not asyncio.current_task()
        )
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.drain()

async def prepare(app: object) -> FailureRuntime | None:
    """
    Resolve an application's failure runtime without activating observation.

    Parameters
    ----------
    app : object
        Application whose configured exception handler should be prepared.

    Returns
    -------
    FailureRuntime or None
        Prepared runtime, or ``None`` if no runtime exists and the application
        is uncreated or lacks a catch binding.
    """
    runtime = _find_runtime(app)
    if runtime is None:
        if getattr(app, "isCreated", False) is not True:
            return None
        from orionis.failure.contracts.catch import ICatch  # noqa: PLC0415

        if app.bound(ICatch) is not True:
            return None
        runtime = FailureRuntime(app)
        app._failure_runtime = runtime
    await runtime.prepare()
    return runtime

def _context(
    *,
    runtime: FailureRuntime,
    flow: str,
    phase: str,
    operation: str | None,
    correlation_id: str | None,
    expected: bool,
    metadata: Mapping[str, object] | None,
) -> FailureContext:
    """
    Build failure metadata using compatible operation defaults.

    Parameters
    ----------
    runtime : FailureRuntime
        Runtime whose current operation can supply inherited metadata.
    flow : str
        Flow label; inherit the current flow when set to ``"runtime"``.
    phase : str
        Failure phase to record.
    operation : str or None
        Explicit operation name, or ``None`` to inherit the current name.
    correlation_id : str or None
        Explicit correlation identifier, or ``None`` to inherit one.
    expected : bool
        Whether the execution owner classifies this as an expected failure.
    metadata : collections.abc.Mapping[str, object] or None
        Additional incident metadata to sanitize, or ``None`` for no metadata.

    Returns
    -------
    FailureContext
        Immutable, sanitized context enriched by the current matching operation.
    """
    current = _current.get()
    if current is not None and current.runtime is not runtime:
        current = None
    if current is not None:
        if flow == "runtime":
            flow = current.flow
        if operation is None:
            operation = current.name
        if correlation_id is None:
            correlation_id = current.correlation_id
    return FailureContext(
        flow=flow,
        phase=phase,
        operation=operation,
        correlation_id=correlation_id,
        expected=expected,
        metadata=metadata or {},
    )

async def capture(
    exception: BaseException,
    *,
    app: object | None = None,
    runtime: FailureRuntime | None = None,
    flow: str = "runtime",
    phase: str = "execution",
    operation: str | None = None,
    correlation_id: str | None = None,
    expected: bool = False,
    metadata: Mapping[str, object] | None = None,
) -> FailureReceipt | None:
    """
    Observe an exception through an active application runtime.

    Inherit flow, operation name, and correlation from a matching operation when
    their default values are used. Leave presentation and recovery to the caller.

    Parameters
    ----------
    exception : BaseException
        Original exception instance to observe.
    app : object or None, optional
        Application used to locate a runtime when none is supplied.
    runtime : FailureRuntime or None, optional
        Explicit runtime; otherwise resolve one from the application or operation.
    flow : str, optional
        Execution-flow label; inherit the current flow when ``"runtime"``.
    phase : str, optional
        Failure phase. Defaults to ``"execution"``.
    operation : str or None, optional
        Logical operation name; inherit the current name when ``None``.
    correlation_id : str or None, optional
        Correlation identifier; inherit the current value when ``None``.
    expected : bool, default False
        Mark the failure as expected for reporting policy.
    metadata : collections.abc.Mapping[str, object] or None, optional
        Additional incident metadata to copy, bound, and redact.

    Returns
    -------
    FailureReceipt or None
        Delivery status, or ``None`` when no runtime is active or the failure
        represents cancellation or process control.

    Raises
    ------
    BaseException
        If observation is interrupted by cancellation or a reporting-path
        control-flow exception.
    """
    runtime = runtime if isinstance(runtime, FailureRuntime) else get_runtime(app)
    if runtime is None or not runtime.active:
        return None
    return await runtime.capture(
        exception,
        context=_context(
            runtime=runtime,
            flow=flow,
            phase=phase,
            operation=operation,
            correlation_id=correlation_id,
            expected=expected,
            metadata=metadata,
        ),
    )

async def capture_result(
    value: object,
    *,
    app: object | None = None,
    runtime: FailureRuntime | None = None,
    flow: str = "runtime",
    phase: str = "result",
    operation: str | None = None,
    correlation_id: str | None = None,
    expected: bool = True,
    metadata: Mapping[str, object] | None = None,
) -> FailureReceipt | None:
    """
    Observe a declared failed result through an active runtime.

    Preserve the result without synthesizing an exception or traceback.

    Parameters
    ----------
    value : object
        Original result classified as a failure by its execution owner.
    app : object or None, optional
        Application used to locate a runtime when none is supplied.
    runtime : FailureRuntime or None, optional
        Explicit runtime; otherwise resolve one from the application or operation.
    flow : str, optional
        Execution-flow label; inherit the current flow when ``"runtime"``.
    phase : str, optional
        Failure phase. Defaults to ``"result"``.
    operation : str or None, optional
        Logical operation name; inherit the current name when ``None``.
    correlation_id : str or None, optional
        Correlation identifier; inherit the current value when ``None``.
    expected : bool, default True
        Mark the result as expected for reporting policy.
    metadata : collections.abc.Mapping[str, object] or None, optional
        Additional incident metadata to copy, bound, and redact.

    Returns
    -------
    FailureReceipt or None
        Delivery and reporting status, or ``None`` when no runtime is active.

    Raises
    ------
    BaseException
        If cancellation or a control-flow error escapes application policy.
    """
    runtime = runtime if isinstance(runtime, FailureRuntime) else get_runtime(app)
    if runtime is None or not runtime.active:
        return None
    return await runtime.captureResult(
        value,
        context=_context(
            runtime=runtime,
            flow=flow,
            phase=phase,
            operation=operation,
            correlation_id=correlation_id,
            expected=expected,
            metadata=metadata,
        ),
    )

def _completed_receipt(
    loop: asyncio.AbstractEventLoop, running: asyncio.AbstractEventLoop | None,
    receipt: FailureReceipt,
) -> asyncio.Future | Future:
    """
    Return a completed receipt future for the caller's event-loop context.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        Runtime event loop used for same-loop callers.
    running : asyncio.AbstractEventLoop or None
        Caller's event loop, or ``None`` outside an async event loop.
    receipt : FailureReceipt
        Delivery status used to complete the returned future.

    Returns
    -------
    asyncio.Future or concurrent.futures.Future
        Completed asyncio future on the runtime loop, or a thread-safe future
        for callers outside that loop.
    """
    complete = loop.create_future() if running is loop else ThreadFuture()
    complete.set_result(receipt)
    return complete

def _pending_incident(
    runtime: FailureRuntime, exception: BaseException, context: FailureContext,
) -> tuple[FailureContext, _Incident | None, FailureReceipt | None]:
    """
    Claim or reuse callback incident identity while its operation is live.

    Parameters
    ----------
    runtime : FailureRuntime
        Runtime owning the pending report and its claim lock.
    exception : BaseException
        Original exception whose identity must be claimed before scheduling.
    context : FailureContext
        Metadata to enrich for a new or reclaimed incident.

    Returns
    -------
    tuple[FailureContext, _Incident | None, FailureReceipt | None]
        Resolved context, pending incident, and duplicate receipt; the final
        two entries are mutually exclusive.
    """
    # Copied ContextVars can share one ledger across worker threads. Lookup,
    # event allocation and publication must remain one atomic claim.
    with runtime._pending_lock:
        current = _runtime_operation(runtime)
        incident = current.incident(exception) if current is not None else None
        previous = _previous_receipt(exception, current, incident)
        if previous is not None and (incident is None or not incident.abandoned):
            return context, None, replace(previous, duplicate=True)
        if incident is not None:
            context = incident.context or context
            incident.reclaim()
            context = replace(context, event_id=incident.receipt.event_id)
        else:
            context = replace(context, event_id=uuid4().hex)
            incident = _Incident(exception, FailureReceipt(event_id=context.event_id))
        context = runtime._correlate(context)
        context = _parent_context(exception, context, current)
        if current is not None:
            current.adopt(incident)
        incident.context = context
        return context, incident, None

def capture_nowait(
    exception: BaseException,
    *,
    app: object | None = None,
    runtime: FailureRuntime | None = None,
    flow: str = "runtime",
    phase: str = "execution",
    operation: str | None = None,
    correlation_id: str | None = None,
    expected: bool = False,
    metadata: Mapping[str, object] | None = None,
) -> asyncio.Task | Future | None:
    """
    Schedule supervised exception observation from a callback or worker.

    Claim incident identity before scheduling delivery on the runtime loop.
    Return completed futures for recursive or duplicate observations.

    Parameters
    ----------
    exception : BaseException
        Original exception instance to observe.
    app : object or None, optional
        Application used to locate a runtime when none is supplied.
    runtime : FailureRuntime or None, optional
        Explicit runtime; otherwise resolve one from the application or operation.
    flow : str, optional
        Execution-flow label; inherit the current flow when ``"runtime"``.
    phase : str, optional
        Failure phase. Defaults to ``"execution"``.
    operation : str or None, optional
        Logical operation name; inherit the current name when ``None``.
    correlation_id : str or None, optional
        Correlation identifier; inherit the current value when ``None``.
    expected : bool, default False
        Mark the failure as expected for reporting policy.
    metadata : collections.abc.Mapping[str, object] or None, optional
        Additional incident metadata to copy, bound, and redact.

    Returns
    -------
    asyncio.Task or asyncio.Future or concurrent.futures.Future or None
        Supervised report task or receipt future, or ``None`` when observation
        is inactive or cannot be scheduled. Cross-thread callers receive a
        thread-safe future.
    """
    runtime = runtime if isinstance(runtime, FailureRuntime) else get_runtime(app)
    if runtime is None or not runtime.active:
        return None
    context = _context(
        runtime=runtime,
        flow=flow,
        phase=phase,
        operation=operation,
        correlation_id=correlation_id,
        expected=expected,
        metadata=metadata,
    )
    loop = runtime._loop
    if loop is None or loop.is_closed():
        _emergency(exception, context)
        return None

    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None

    if _reporting.get() is runtime:
        context = replace(context, event_id=uuid4().hex)
        _emergency(exception, context)
        return _completed_receipt(
            loop, running, FailureReceipt(event_id=context.event_id, degraded=True),
        )

    context, incident, previous = _pending_incident(runtime, exception, context)
    if previous is not None:
        return _completed_receipt(loop, running, previous)

    def done(task: asyncio.Task) -> None:
        """
        Collect callback-report failures and release pending ownership.

        Parameters
        ----------
        task : asyncio.Task
            Loop-side reporting task that has completed.

        Returns
        -------
        None
            Remove the task, abandon an unstarted claim, and emit fallback
            diagnostics for an exceptional report exit.
        """
        runtime._pending.discard(task)
        incident.abandon()
        error = None if task.cancelled() else task.exception()
        if error is not None:
            _emergency(exception, context, error)

    if running is loop:
        task = loop.create_task(runtime.capture(
            exception, context=context, _incident=incident,
        ))
        runtime._pending.add(task)
        task.add_done_callback(done)
        return task

    return _submit_thread(runtime, loop, exception, context, incident)

def _submit_thread(
    runtime: FailureRuntime, loop: asyncio.AbstractEventLoop,
    exception: BaseException, context: FailureContext, incident: _Incident,
) -> Future | None:
    """
    Submit and track failure delivery on the runtime's event loop.

    Parameters
    ----------
    runtime : FailureRuntime
        Runtime retaining ownership of the cross-thread report.
    loop : asyncio.AbstractEventLoop
        Event loop on which delivery must run.
    exception : BaseException
        Original failure to deliver.
    context : FailureContext
        Incident metadata already claimed by the originating callback.
    incident : _Incident
        Pending incident whose completion must be retained or abandoned.

    Returns
    -------
    concurrent.futures.Future or None
        Thread-safe delivery future, or ``None`` after a scheduling failure has
        been diagnosed and the incident abandoned.
    """
    coroutine = runtime.capture(exception, context=context, _incident=incident)
    try:
        # Publish submission and ownership together: drain must not finish
        # between scheduling a thread's coroutine and registering its future.
        with runtime._pending_lock:
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            runtime._thread_pending.add(future)
    except RuntimeError as secondary:
        coroutine.close()
        incident.abandon()
        _emergency(exception, context, secondary)
        return None
    def finished(result: Future) -> None:
        """
        Collect a cross-thread report outcome and release its registration.

        Parameters
        ----------
        result : concurrent.futures.Future
            Completed thread-safe future for a loop-side report.

        Returns
        -------
        None
            Drop pending ownership, abandon an unstarted incident, and diagnose
            an exceptional result without treating cancellation as a failure.
        """
        with runtime._pending_lock:
            runtime._thread_pending.discard(result)
        incident.abandon()
        if not result.cancelled():
            error = result.exception()
            if error is not None:
                _emergency(exception, context, error)

    future.add_done_callback(finished)
    return future

def is_reporting() -> bool:
    """
    Check whether the current context is executing a failure reporter.

    Returns
    -------
    bool
        ``True`` if a reporting runtime is bound, otherwise ``False``.
    """
    return _reporting.get() is not None

def reporting_runtime() -> FailureRuntime | None:
    """
    Return the reporter identity bound to the current context.

    Returns
    -------
    FailureRuntime or None
        Current reporting runtime, or ``None`` outside reporter execution.
    """
    return _reporting.get()

@contextmanager
def reporting_from(runtime: FailureRuntime) -> Generator[None]:
    """
    Bind a reporter identity while processing its queued log record.

    Parameters
    ----------
    runtime : FailureRuntime
        Runtime whose reporter identity should be restored for the sink.

    Yields
    ------
    None
        Keep the runtime bound for the block and restore the previous identity
        on exit.
    """
    token = _reporting.set(runtime)
    try:
        yield
    finally:
        _reporting.reset(token)
