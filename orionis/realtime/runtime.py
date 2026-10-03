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

class HubRuntime:
    """Execute a precompiled Hub using the existing application and scopes."""

    __slots__ = ("_app", "_dispatch", "_hub", "_manager", "_protocol")

    def __init__(
        self, app: IApplication, manager: IConnectionManager,
        hub: type[Hub], protocol: str = "json",
    ) -> None:
        """
        Compile trusted Hub metadata before accepting network messages.

        Parameters
        ----------
        app : IApplication
            Existing application and dependency container.
        manager : IConnectionManager
            Shared worker-local registry and targeting service.
        hub : type[Hub]
            Application-declared Hub class.
        protocol : str, optional
            JSON or MessagePack selected by the route.

        Returns
        -------
        None
            Store runtime dependencies and compile dispatch and codec metadata.

        Raises
        ------
        TypeError
            If the Hub class, remote descriptors or annotations are unsupported.
        ValueError
            If remote names, aliases, protocol or message size are invalid.
        """
        self._app = app
        self._manager = manager
        self._hub = hub
        self._dispatch = compile_hub(hub)
        self._protocol = HubProtocol(
            protocol, max_message_size=manager.config.max_message_size,
        )

    def _bindContext(
        self, scope: ScopeManager, connection: RealtimeConnection,
    ) -> None:
        """
        Publish connection primitives into an independent scope.

        Parameters
        ----------
        scope : ScopeManager
            Active connection or invocation scope.
        connection : RealtimeConnection
            Owner of network state.

        Returns
        -------
        None
            Register the socket, context, connection, client and group proxies,
            and HTTP kernel marker in the supplied scope.
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
        Construct a fresh Hub and attach its scoped connection primitives.

        Parameters
        ----------
        connection : RealtimeConnection
            Connection used for lifecycle and client targeting.

        Returns
        -------
        Hub
            Fresh instance with constructor injection resolved.
        """
        instance = await self._app.build(self._hub)
        instance.context = connection.context
        instance.clients = await self._app.make(HubClients)
        instance.groups = await self._app.make(HubGroups)
        return instance

    async def serve(self, socket: WebSocket) -> None:
        """
        Run one Hub connection and release all resources before returning.

        Parameters
        ----------
        socket : WebSocket
            Socket already registered in a kernel connection scope.

        Returns
        -------
        None
            Run connection hooks and message handling, then release owned work,
            registry membership and socket resources.

        Raises
        ------
        RuntimeError
            If called without the application's active connection scope.
        asyncio.CancelledError
            If the connection owner is cancelled without a recorded failure.
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
        )
        self._bindContext(scope, connection)
        self._manager.register(connection)
        code, reason = 1000, ""
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
            code = exc.close_code
            reason = "Invalid realtime message"
            _LOGGER.warning("Realtime protocol violation")
        except WebSocketDisconnected as exc:
            code, reason = exc.code, exc.reason
        except asyncio.CancelledError: # NOSONAR
            code = 1001
            if connection.failure is not None:
                code = 1011
                raise connection.failure from None
            raise
        except Exception:
            code = 1011
            raise
        finally:
            try:
                await connection.cleanup()
            finally:
                self._manager.unregister(connection)
                await self._disconnect(connection, code, reason)

    async def _disconnect(
        self, connection: RealtimeConnection, code: int, reason: str,
    ) -> None:
        """
        Run the final hook without allowing it to prevent socket cleanup.

        Parameters
        ----------
        connection : RealtimeConnection
            Already unregistered connection.
        code : int
            Observed or locally selected closure code.
        reason : str
            Peer reason where available.

        Returns
        -------
        None
            Bound the disconnect hook to five seconds, log hook failures and
            close the socket if it remains open.

        Raises
        ------
        asyncio.CancelledError
            If the final hook or socket closure is cancelled.
        """
        try:
            async with asyncio.timeout(5):
                hook = await self._buildHub(connection)
                await hook.onDisconnect(code, reason)
        except Exception:  # noqa: BLE001 - A user hook must not prevent cleanup.
            _LOGGER.error("Hub disconnect hook failed")  # noqa: TRY400
        finally:
            socket = connection.socket
            if not socket.closed:
                wire_code = code if socket.supportsCloseDetails else 1000
                # Peer-only status codes cannot be emitted in close frames.
                if wire_code in (1005, 1006, 1015):
                    wire_code = 1000
                await socket.close(code=wire_code)

    async def _receive(self, connection: RealtimeConnection) -> tuple[int, str]:
        """
        Keep the sole reader available while invocations execute concurrently.

        Parameters
        ----------
        connection : RealtimeConnection
            Ready connection with finite owned task registries.

        Returns
        -------
        tuple[int, str]
            Peer close code and reason, or (1000, "") when local reading stops.

        Raises
        ------
        ProtocolError
            If decoding fails or an active invocation identifier is reused.
        WebSocketDisconnected
            If socket operations report a disconnected peer.
        asyncio.CancelledError
            If the connection reader is cancelled.
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
        Validate admission before allocating an invocation task.

        Parameters
        ----------
        connection : RealtimeConnection
            Connection owning the invocation ID namespace.
        envelope : Invoke
            Structurally validated client invocation.

        Returns
        -------
        None
            Register an admitted invocation task or send a controlled rejection.

        Raises
        ------
        ProtocolError
            If an active invocation ID is reused.
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
        Execute one remote method inside its own contextvars-backed scope.

        Parameters
        ----------
        connection : RealtimeConnection
            Owner of tasks and response delivery.
        method : RemoteMethod
            Boot-compiled callable and binding metadata.
        envelope : Invoke
            Validated client values, never executable metadata.
        auth : AuthenticationContext
            Fresh authentication context with independent authorization cache.

        Returns
        -------
        None
            Resolve dependencies, execute the method and send its result or a
            sanitized error after invocation-scope cleanup.

        Raises
        ------
        asyncio.CancelledError
            If the invocation is cancelled after attempting its error response.
        """
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
                kwargs = method.bind(envelope.args, envelope.kwargs)
                for name, dependency in method.dependencies.items():
                    kwargs[name] = await self._app.make(dependency)
                instance = await self._buildHub(connection)
                result = await self._app.call(instance, method.method_name, **kwargs)
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
                connection, envelope.id, "cancelled", streaming=streaming,
            )
            raise
        except RPCError as exc:
            await self._error(connection, envelope.id, exc.code, streaming=streaming)
        except AuthenticationException:
            await self._error(
                connection, envelope.id, "unauthorized", streaming=streaming,
            )
        except AuthorizationException:
            await self._error(
                connection, envelope.id, "forbidden", streaming=streaming,
            )
        except TimeoutError:
            await self._error(
                connection, envelope.id, "timeout", streaming=streaming,
            )
        except Exception:  # noqa: BLE001 - Sanitize arbitrary application failures.
            await self._error(
                connection, envelope.id, "internal_error", streaming=streaming,
            )

    async def _stream(
        self, connection: RealtimeConnection, invocation_id: str,
        source: AsyncIterable[object],
    ) -> None:
        """
        Deliver each item before advancing the producer and close its iterator.

        Parameters
        ----------
        connection : RealtimeConnection
            Connection providing natural send backpressure.
        invocation_id : str
            Correlation ID selected at admission.
        source : AsyncIterable[object]
            Application-produced asynchronous stream.

        Returns
        -------
        None
            Send correlated stream items and await iterator closure when an
            ``aclose`` method is available.

        Raises
        ------
        TypeError, ValueError
            If a stream item cannot be encoded by the selected codec.
        ConnectionError
            If connection cleanup has started during delivery.
        asyncio.CancelledError
            If streaming is cancelled while producing, sending or closing.
        """
        iterator = cast("AsyncIterator[object]", aiter(source))
        try:
            async for item in iterator:
                await connection.send({
                    "type": "stream_item", "id": invocation_id, "item": item,
                })
        finally:
            close = getattr(iterator, "aclose", None)
            if close is not None:
                await close()

    @staticmethod
    async def _error(
        connection: RealtimeConnection, invocation_id: str, code: str,
        *, streaming: bool = False,
    ) -> None:
        """
        Send a controlled error without exposing application exception text.

        Parameters
        ----------
        connection : RealtimeConnection
            Response destination.
        invocation_id : str
            Previously validated correlation ID.
        code : str
            Stable error classification.
        streaming : bool, optional
            Whether to terminate a stream instead of a scalar invocation.

        Returns
        -------
        None
            Release active invocation ownership and send a terminal error, or
            skip delivery when the connection is closing or already closed.

        Raises
        ------
        ConnectionError
            If connection cleanup starts before the write acquires ownership.
        asyncio.CancelledError
            If terminal error delivery is cancelled.
        """
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
