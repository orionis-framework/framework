"""Execute a precompiled Hub using the existing application and scopes."""

import asyncio
import logging
import secrets
from collections.abc import AsyncIterable
from functools import partial
from typing import TYPE_CHECKING, cast
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context, current_auth_context
from orionis.auth.exceptions import AuthenticationException, AuthorizationException
from orionis.failure.enums.kernel_type import KernelContext
from orionis.failure.runtime import capture, capture_result, get_runtime, operation
from orionis.http import WebSocket, WebSocketDisconnected
from orionis.realtime.clients import HubClients
from orionis.realtime.connection import RealtimeConnection
from orionis.realtime.errors import ProtocolError, RPCError
from orionis.realtime.groups import HubGroups
from orionis.realtime.hub import Hub, HubContext
from orionis.realtime.metadata import compile_hub
from orionis.realtime.protocol import Cancel, Completion, HubProtocol, Invoke, Ping

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from orionis.container.context.manager import ScopeManager
    from orionis.foundation.contracts.application import IApplication
    from orionis.realtime.contracts.manager import IConnectionManager
    from orionis.realtime.metadata import RemoteMethod

_LOGGER = logging.getLogger(__name__)
"""Logger used by ``runtime``."""

class HubRuntime:
    """Execute a precompiled Hub using the existing application and scopes."""

    __slots__ = ("_app", "_dispatch", "_hub", "_manager", "_protocol")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self, app: IApplication, manager: IConnectionManager,
        hub: type[Hub], protocol: str = "json",
    ) -> None:
        """
        Bind application services and compile a Hub's remote dispatch metadata.

        Parameters
        ----------
        app : orionis.IApplication
            Existing application used for dependency resolution and scoped execution.
        manager : orionis.realtime.contracts.manager.IConnectionManager
            Shared connection registry and client-targeting service.
        hub : type[orionis.realtime.Hub]
            Hub class whose remote methods and lifecycle hooks should run.
        protocol : str, optional
            Route-selected JSON or MessagePack codec name.

        Returns
        -------
        None
            Store services and compile the Hub method table and selected codec.

        Raises
        ------
        TypeError
            If Hub metadata, remote descriptors, or type annotations are unsupported.
        ValueError
            If remote names, aliases, protocol, or message-size settings are invalid.
        """
        self._app = app
        """Existing application and dependency container."""
        self._manager = manager
        """Shared worker-local registry and targeting service."""
        self._hub = hub
        """Application-declared Hub class."""
        self._dispatch = compile_hub(hub)
        """Dispatch produced by ``compile_hub``."""
        self._protocol = HubProtocol(
            protocol, max_message_size=manager.config.max_message_size,
        )
        """JSON or MessagePack selected by the route."""

    def _bindContext(
        self, scope: ScopeManager, connection: RealtimeConnection,
    ) -> None:
        """
        Bind connection state and targeting helpers into the supplied scope.

        Parameters
        ----------
        scope : orionis.container.context.manager.ScopeManager
            Active connection or invocation dependency scope to populate.
        connection : orionis.realtime.connection.RealtimeConnection
            Connection supplying the socket, identity, and Hub namespace.

        Returns
        -------
        None
            Register socket, context, connection, client/group helpers, and the HTTP
            kernel marker.
        """
        scope[WebSocket] = connection.socket
        scope[HubContext] = connection.context
        scope[RealtimeConnection] = connection
        scope[HubClients] = HubClients(
            self._manager, self._hub, connection.context.connection_id,
        )
        scope[HubGroups] = HubGroups(self._manager, connection.context.connection_id)
        scope.set("kernel", KernelContext.HTTP)

    async def _buildHub(self, connection: RealtimeConnection) -> Hub:
        """
        Build a Hub instance and attach connection-scoped client/group helpers.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Connection supplying lifecycle context and client targeting.

        Returns
        -------
        orionis.realtime.Hub
            Hub with constructor dependencies, context, clients, and groups bound.
        """
        instance = await self._app.build(self._hub)
        instance.context = connection.context
        instance.clients = await self._app.make(HubClients)
        instance.groups = await self._app.make(HubGroups)
        return instance

    async def serve(self, socket: WebSocket) -> None:
        """
        Serve one scoped Hub connection and finalize its owned work.

        Parameters
        ----------
        socket : orionis.http.WebSocket
            WebSocket already bound to the application's active connection scope.

        Returns
        -------
        None
            Run connection hooks and message dispatch, then remove registry ownership
            and close the socket.

        Raises
        ------
        RuntimeError
            If the application has no active connection scope.
        asyncio.CancelledError
            If owner cancellation is not replaced by a recorded fatal task failure.
        BaseException
            If a fatal child, connection hook, or finalization failure escapes.
        """
        scope = self._app.getCurrentScope()
        if scope is None:
            message = "A Hub requires an active connection scope"
            raise RuntimeError(message)
        auth = current_auth_context()
        context = HubContext(
            connection_id=secrets.token_urlsafe(24), socket=socket,
            user=auth.identity,
        )
        connection = RealtimeConnection(
            context, self._hub, self._protocol, self._manager.config,
            runtime=get_runtime(self._app),
        )
        self._bindContext(scope, connection)
        self._manager.register(connection)
        with operation(
            self._app, flow="realtime", operation=self._hub.__name__,
            correlation_id=context.connection_id,
        ):
            connection.bindFailureOperation()
            code, reason = 1000, ""
            original = None
            try:
                hook = await self._buildHub(connection)
                await hook.onConnect()
                if socket.closed:
                    return
                if not socket.accepted:
                    await socket.accept()
                # The ready write acquires ownership before the next scheduling point.
                connection.ready = True
                await connection.send({
                    "type": "ready", "version": 1,
                    "connection_id": context.connection_id,
                })
                code, reason = await self._receive(connection)
            except ProtocolError as exc:
                await capture(
                    exc, app=self._app, flow="realtime", phase="protocol",
                    correlation_id=context.connection_id, expected=True,
                )
                code = exc.close_code
                reason = "Invalid realtime message"
            except WebSocketDisconnected as exc:
                code, reason = exc.code, exc.reason
            except asyncio.CancelledError as exc: # NOSONAR
                code = 1001
                original = exc
                if connection.failure is not None:
                    code = 1011
                    original = connection.failure
                    await capture(
                        connection.failure, app=self._app, flow="realtime",
                        phase="connection", correlation_id=context.connection_id,
                    )
                    # Keep the original transport cause across owner cancellation.
                    raise connection.failure from connection.failure.__cause__
                raise
            except BaseException as exc:
                original = exc
                await capture(
                    exc, app=self._app, flow="realtime", phase="connection",
                    correlation_id=context.connection_id,
                )
                code = 1011
                raise
            finally:
                await self._finishConnection(connection, code, reason, original)

    async def _finishConnection(
        self, connection: RealtimeConnection, code: int, reason: str,
        original: BaseException | None,
    ) -> None:
        """
        Finalize connection work while preserving an escaping primary failure.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Connection whose work, registration, and disconnect hook need cleanup.
        code : int
            Selected close status passed to disconnect handling.
        reason : str
            Peer or local close reason supplied to the disconnect hook.
        original : BaseException or None
            Failure already escaping from the connection body, if any.

        Returns
        -------
        None
            Join owned cleanup, unregister the connection, and run disconnect handling.

        Raises
        ------
        BaseException
            If finalization fails; preserve ``original`` when present, otherwise
            keep a prior cleanup failure primary over a later close failure.
        """
        cleanup_error = None
        try:
            await connection.cleanup()
        except BaseException as exc:
            cleanup_error = exc
            await capture(
                exc, app=self._app, flow="realtime", phase="cleanup",
                correlation_id=connection.context.connection_id,
            )
            if original is not None:
                raise original from exc
            raise
        finally:
            try:
                self._manager.unregister(connection)
                await self._disconnect(connection, code, reason)
            except BaseException as exc:
                await capture(
                    exc, app=self._app, flow="realtime", phase="close",
                    correlation_id=connection.context.connection_id,
                )
                if original is not None:
                    raise original from exc
                if cleanup_error is not None:
                    raise cleanup_error from exc
                raise

    async def _disconnect(
        self, connection: RealtimeConnection, code: int, reason: str,
    ) -> None:
        """
        Run the disconnect hook with a deadline, then close any open socket.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Connection already removed from the manager's registry.
        code : int
            Status supplied to the hook and normalized for the outbound close frame.
        reason : str
            Reason supplied to ``onDisconnect``, not sent in the close frame.

        Returns
        -------
        None
            Bound the hook to five seconds, observe ordinary hook failures, and
            close an open socket with an admissible wire status.

        Raises
        ------
        asyncio.CancelledError
            If the hook or socket closure is cancelled.
        BaseException
            If socket closure or another unhandled disconnect operation fails.
        """
        try:
            async with asyncio.timeout(5):
                hook = await self._buildHub(connection)
                await hook.onDisconnect(code, reason)
        except Exception as exc:  # noqa: BLE001 - Preserve socket cleanup.
            receipt = await capture(
                exc, app=self._app, flow="realtime", phase="disconnect_hook",
                correlation_id=connection.context.connection_id,
            )
            if receipt is None:
                _LOGGER.error("Hub disconnect hook failed")  # noqa: TRY400
        finally:
            socket = connection.socket
            if not socket.closed:
                wire_code = code if socket.supportsCloseDetails else 1000
                # Peer-only status codes cannot be emitted in close frames.
                if wire_code in (1005, 1006, 1015):
                    wire_code = 1000
                try:
                    await socket.close(code=wire_code)
                except BaseException as exc:
                    await capture(
                        exc, app=self._app, flow="realtime", phase="close",
                        correlation_id=connection.context.connection_id,
                    )
                    raise

    async def _receive(self, connection: RealtimeConnection) -> tuple[int, str]:
        """
        Read Hub messages while admitted invocations execute concurrently.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Ready connection whose socket this method owns as the sole reader.

        Returns
        -------
        tuple[int, str]
            Peer disconnect code and reason, or ``(1000, "")`` when local reading ends.

        Raises
        ------
        orionis.realtime.errors.ProtocolError
            If decoding fails or an active invocation ID is reused.
        orionis.http.WebSocketDisconnected
            If socket operations report peer disconnection.
        asyncio.CancelledError
            If the connection's reader task is cancelled.
        """
        while not connection.closing and not connection.socket.closed:
            message = await connection.socket.receive()
            if message.isDisconnect():
                return message.code or 1006, message.reason or ""
            envelope = connection.protocol.decode(message)
            if isinstance(envelope, Invoke):
                await self._startInvocation(connection, envelope)
            elif isinstance(envelope, Completion):
                connection.complete(envelope)
            elif isinstance(envelope, Cancel):
                connection.cancel(envelope.id)
            elif isinstance(envelope, Ping):
                await connection.send({"type": "pong"})
        return 1000, ""

    async def _startInvocation(
        self, connection: RealtimeConnection, envelope: Invoke,
    ) -> None:
        """
        Admit a validated client invocation or send a controlled rejection.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Connection owning invocation IDs, task capacity, and client delivery.
        envelope : orionis.realtime.protocol.Invoke
            Decoded invocation to check against compiled methods and limits.

        Returns
        -------
        None
            Register a task with forked authentication state, or send a rejection
            for method, concurrency, timeout, or context failures.

        Raises
        ------
        orionis.realtime.errors.ProtocolError
            If the client reuses an active invocation ID.
        """
        if envelope.id in connection.active:
            message = "Duplicate active invocation ID"
            raise ProtocolError(message)
        method = self._dispatch.get(envelope.target)
        if method is None:
            await self._error(connection, envelope.id, "method_not_found")
            return
        if (
            len(connection.active) + len(connection.finishing)
            >= connection.config.max_concurrent_invocations
        ):
            await self._error(connection, envelope.id, "busy")
            return
        if (
            envelope.timeout is not None
            and envelope.timeout > connection.config.invocation_timeout
        ):
            await self._error(connection, envelope.id, "invalid_arguments")
            return
        source = current_auth_context()
        if not isinstance(source, AuthenticationContext):
            await self._error(connection, envelope.id, "internal_error")
            return
        # Fork while the connection's identity still owns the current scope.
        auth = source._fork()  # noqa: SLF001 - Internal Auth scope handoff.
        task = asyncio.create_task(
            self._invoke(connection, method, envelope, auth),
        )
        connection.active[envelope.id] = task
        task.add_done_callback(partial(connection.invocationDone, envelope.id))

    async def _invoke(
        self, connection: RealtimeConnection, method: RemoteMethod,
        envelope: Invoke, auth: AuthenticationContext,
    ) -> None:
        """
        Execute one remote method with isolated dependencies and authentication.

        Defer terminal delivery until producer cleanup and invocation-scope exit
        have run.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Owner of invocation tasks and response delivery.
        method : orionis.realtime.metadata.RemoteMethod
            Compiled method, argument bindings, and dependency metadata.
        envelope : orionis.realtime.protocol.Invoke
            Validated client values and optional invocation timeout.
        auth : orionis.auth.context.context.AuthenticationContext
            Forked authentication state with an independent authorization cache.

        Returns
        -------
        None
            Send scalar completion, stream termination, or a sanitized failure
            after exiting the invocation scope.

        Raises
        ------
        asyncio.CancelledError
            If the invocation is cancelled, after attempting its terminal response.
        BaseException
            If terminal delivery, cleanup, or unhandled control flow escapes the
            invocation boundary.
        """
        with operation(
            self._app, flow="realtime", operation=envelope.target,
            correlation_id=envelope.id, isolated=True,
        ):
            streaming = method.is_stream
            timeout = (
                envelope.timeout if envelope.timeout is not None or streaming
                else connection.config.invocation_timeout
            )
            try:
                async with (
                    self._app.beginScope() as scope,
                    asyncio.timeout(timeout) as deadline,
                ):
                    self._bindContext(scope, connection)
                    bind_auth_context(auth)
                    kwargs = await method.bind(envelope.args, envelope.kwargs)
                    for name, dependency in method.dependencies.items():
                        kwargs[name] = await self._app.make(dependency)
                    instance = await self._buildHub(connection)
                    result = await self._app.call(
                        instance, method.method_name, **kwargs,
                    )
                    if isinstance(result, AsyncIterable):
                        streaming = True
                        if envelope.timeout is None:
                            deadline.reschedule(None)
                        await self._stream(connection, envelope.id, result)
                # Final delivery follows producer/scope cleanup and is not governed
                # by the method deadline. Its task stays owned and budgeted until sent.
                connection.finish(envelope.id)
                await connection.send(
                    {"type": "stream_complete", "id": envelope.id} if streaming else
                    {"type": "completion", "id": envelope.id, "result": result},
                )
            except asyncio.CancelledError:
                await self._error(
                    connection, envelope.id, "cancelled",
                    streaming=streaming, observed=True,
                )
                raise
            except RPCError as exc:
                await capture(
                    exc, app=self._app, flow="realtime", phase="invocation",
                    operation=envelope.target, correlation_id=envelope.id,
                    expected=True,
                )
                await self._error(
                    connection, envelope.id, exc.code,
                    streaming=streaming, observed=True,
                )
            except AuthenticationException as exc:
                await capture(
                    exc, app=self._app, flow="realtime", phase="authentication",
                    operation=envelope.target, correlation_id=envelope.id,
                    expected=True,
                )
                await self._error(
                    connection, envelope.id, "unauthorized",
                    streaming=streaming, observed=True,
                )
            except AuthorizationException as exc:
                await capture(
                    exc, app=self._app, flow="realtime", phase="authorization",
                    operation=envelope.target, correlation_id=envelope.id,
                    expected=True,
                )
                await self._error(
                    connection, envelope.id, "forbidden",
                    streaming=streaming, observed=True,
                )
            except TimeoutError as exc:
                await capture(
                    exc, app=self._app, flow="realtime", phase="timeout",
                    operation=envelope.target, correlation_id=envelope.id,
                    expected=True,
                )
                await self._error(
                    connection, envelope.id, "timeout",
                    streaming=streaming, observed=True,
                )
            except Exception as exc:  # noqa: BLE001 - Sanitize application failures.
                await capture(
                    exc, app=self._app, flow="realtime", phase="invocation",
                    operation=envelope.target, correlation_id=envelope.id,
                )
                await self._error(
                    connection, envelope.id, "internal_error",
                    streaming=streaming, observed=True,
                )

    async def _stream(
        self, connection: RealtimeConnection, invocation_id: str,
        source: AsyncIterable[object],
    ) -> None:
        """
        Deliver stream items with send backpressure and close the source iterator.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Connection whose serialized writes govern producer backpressure.
        invocation_id : str
            Invocation identifier attached to each stream item.
        source : collections.abc.AsyncIterable[object]
            Application-produced iterable whose iterator owns streaming cleanup.

        Returns
        -------
        None
            Finish ordered item delivery and invoke the iterator's optional
            asynchronous close hook.

        Raises
        ------
        BaseException
            If iteration, encoding, delivery, or cleanup fails, including
            cancellation. Preserve the primary failure if cleanup also fails.
        """
        iterator = cast("AsyncIterator[object]", aiter(source))
        original = None
        try:
            async for item in iterator:
                await connection.send({
                    "type": "stream_item", "id": invocation_id, "item": item,
                })
        except BaseException as exc:
            original = exc
            await capture(
                exc, app=self._app, flow="realtime", phase="stream",
                correlation_id=invocation_id,
                expected=isinstance(exc, (
                    RPCError, AuthenticationException, AuthorizationException,
                    TimeoutError,
                )),
            )
            raise
        finally:
            close = getattr(iterator, "aclose", None)
            if close is not None:
                try:
                    await close()
                except BaseException as exc:
                    await capture(
                        exc, app=self._app, flow="realtime", phase="cleanup",
                        correlation_id=invocation_id,
                    )
                    if original is not None:
                        raise original from exc
                    raise

    @staticmethod
    async def _error(
        connection: RealtimeConnection, invocation_id: str, code: str,
        *, streaming: bool = False, observed: bool = False,
    ) -> None:
        """
        Send a sanitized terminal error with optional admission observation.

        Parameters
        ----------
        connection : orionis.realtime.connection.RealtimeConnection
            Destination connection and failure-observation runtime.
        invocation_id : str
            Validated identifier used for response and incident correlation.
        code : str
            Stable classification controlling the public error code and safe message.
        streaming : bool, optional
            Terminate a stream instead of a scalar invocation.
        observed : bool, optional
            Suppress duplicate admission observation for an already reported failure.

        Returns
        -------
        None
            Send the terminal envelope after releasing any ID owned by the current
            task; skip writes to a closing or closed connection.

        Raises
        ------
        ConnectionError
            If connection shutdown starts before the write acquires ownership.
        asyncio.CancelledError
            If the terminal delivery wait is cancelled.
        """
        if not observed and code != "cancelled":
            await capture_result(
                code, runtime=connection.failureRuntime, flow="realtime",
                phase="admission", correlation_id=invocation_id,
                expected=code != "internal_error",
            )
        if connection.closing or connection.socket.closed:
            return
        connection.finish(invocation_id)
        await connection.send({
            "type": "stream_complete" if streaming else "completion",
            "id": invocation_id,
            "error": {
                "code": code,
                "message": (
                    "Internal server error" if code == "internal_error"
                    else "Invocation failed"
                ),
            },
        })
