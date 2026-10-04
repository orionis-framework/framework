"""Opt MCP routes into the existing Application disconnect watchers by default."""

import asyncio
from types import SimpleNamespace
import unittest

from orionis.foundation.application import Application
from orionis.http.contracts.kernel import IKernelHTTP


class _PolicyKernel(IKernelHTTP):
    """Simulate a long buffered response before any response bytes are available."""

    __slots__ = ("cleaned", "started")

    def __init__(self) -> None:
        """Create deterministic invocation and cleanup boundaries."""
        self.started = asyncio.Event()
        self.cleaned = asyncio.Event()

    async def boot(self) -> None:
        """Expose the same completed boot contract as the native kernel."""

    def disconnectPaths(self) -> frozenset[str]:
        """Represent the static paths compiled from MCP endpoint policies."""
        return frozenset({"/mcp"})

    async def handleASGI(self, _scope, receive, _send) -> None:
        """Consume the body and suspend until Application cancels the handler."""
        await receive()
        self.started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cleaned.set()

    async def handleRSGI(self, _scope, _protocol) -> None:
        """Suspend a buffered RSGI handler before response creation."""
        self.started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cleaned.set()


class TestProtocolDisconnect(unittest.IsolatedAsyncioTestCase):
    """Select actual Application watchers without enabling global monitoring."""

    async def application(self):
        """Publish a real kernel through the normal boot-and-cache path."""
        application = object.__new__(Application)
        application.__init__()
        application._Application__configured = True
        application._Application__bootstrap = {
            "config": {"app": {}},
            "kernels": {"KernelHTTP": {"module": __name__, "class": "_PolicyKernel"}},
        }
        await application._Application__initializeHttpKernel("asgi")
        self.assertFalse(application._Application__http_disconnect_monitoring)
        self.assertEqual(
            application._Application__http_disconnect_paths,
            frozenset({"/mcp"}),
        )
        return application, application._Application__kernel_http_asgi.__self__

    async def test_buffered_asgi_request_is_cancelled_on_disconnect_by_path(self):
        """Cancel an MCP JSON handler even when the global setting remains false."""
        application, kernel = await self.application()
        messages = asyncio.Queue()
        messages.put_nowait({"type": "http.request", "body": b"{}", "more_body": False})

        async def send(_message):
            self.fail("A cancelled buffered request must not send a response")

        task = asyncio.create_task(
            application._Application__handleHttpAsgi(
                {"type": "http", "path": "/mcp/"},
                messages.get,
                send,
            ),
        )
        await asyncio.wait_for(kernel.started.wait(), 1)
        messages.put_nowait({"type": "http.disconnect"})
        await asyncio.wait_for(task, 1)
        self.assertTrue(kernel.cleaned.is_set())

    async def test_buffered_rsgi_request_is_cancelled_on_disconnect_by_path(self):
        """Reuse Granian's supported notifier for policy-marked RSGI endpoints."""
        application, kernel = await self.application()
        disconnected = asyncio.Event()
        task = asyncio.create_task(
            application._Application__handleHttpRsgi(
                SimpleNamespace(proto="http", path="/mcp"),
                SimpleNamespace(client_disconnect=disconnected.wait),
            ),
        )
        await asyncio.wait_for(kernel.started.wait(), 1)
        disconnected.set()
        await asyncio.wait_for(task, 1)
        self.assertTrue(kernel.cleaned.is_set())
