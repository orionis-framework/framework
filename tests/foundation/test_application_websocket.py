from types import SimpleNamespace
from orionis.test import TestCase
from tests.foundation.test_application_async import _AsyncCall, _new_application

class TestApplicationWebSocketDispatch(TestCase):
    """Exercise WebSocket dispatch without HTTP body-disconnect watchers."""

    async def testAsgiWebSocketUsesKernelWithOriginalCallbacks(self) -> None:
        """Forward a connection directly when HTTP monitoring is enabled.

        Returns
        -------
        None
            Verify ASGI dispatch preserves the original callbacks.
        """
        application = _new_application()
        application._Application__http_disconnect_monitoring = True
        handler = _AsyncCall(return_value="socket")
        application._Application__kernel_http_asgi = handler
        receive, send = _AsyncCall(), _AsyncCall()
        scope = {"type": "websocket"}
        self.assertEqual(await application(scope, receive, send), "socket")
        self.assertEqual(handler.calls, [((scope, receive, send), {})])
        self.assertEqual(receive.awaitCount, 0)

    async def testRsgiWebSocketDoesNotRequireHttpDisconnectProtocol(self) -> None:
        """Accept the ``ws`` protocol without reading HTTP disconnects.

        Returns
        -------
        None
            Verify RSGI dispatch forwards the scope and protocol unchanged.
        """
        application = _new_application()
        application._Application__http_disconnect_monitoring = True
        handler = _AsyncCall(return_value="socket")
        application._Application__kernel_http_rsgi = handler
        scope = SimpleNamespace(proto="ws")
        protocol = object()
        self.assertEqual(await application.__rsgi__(scope, protocol), "socket")
        self.assertEqual(handler.calls, [((scope, protocol), {})])
