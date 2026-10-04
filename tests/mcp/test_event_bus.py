"""Exercise bounded subscriptions, cancellation and process isolation."""

import asyncio
import unittest

from orionis.mcp.protocol.requests import SubscriptionFilter
from orionis.mcp.subscriptions.event_bus import InMemoryMcpEventBus

_TOOLS = "notifications/tools/list_changed"
_RESOURCE = "notifications/resources/updated"


class TestEventBus(unittest.IsolatedAsyncioTestCase):
    """No listener or producer task survives its request."""

    async def test_filter_and_coalescing(self):
        """Coalesce duplicates and ignore events outside the explicit filter."""
        bus = InMemoryMcpEventBus(buffer_size=1)
        stream = bus.listen(type(self), SubscriptionFilter(toolsListChanged=True))
        await bus.publish(type(self), _TOOLS)
        await bus.publish(type(self), _TOOLS)
        await bus.publish(type(self), _RESOURCE, "docs://x")
        self.assertEqual(await anext(stream), (_TOOLS, None))
        await stream.aclose()
        self.assertEqual(bus.listener_count, 0)

    async def test_overflow_closes_instead_of_losing_events(self):
        """A full buffer signals closure so clients can refresh state."""
        bus = InMemoryMcpEventBus(buffer_size=1)
        stream = bus.listen(
            type(self),
            SubscriptionFilter(resourceSubscriptions=("docs://a", "docs://b")),
        )
        await bus.publish(type(self), _RESOURCE, "docs://a")
        await bus.publish(type(self), _RESOURCE, "docs://b")
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertEqual(bus.listener_count, 0)

    async def test_cancel_releases_listener(self):
        """Cancellation while idle releases the request's registration."""
        bus = InMemoryMcpEventBus()
        stream = bus.listen(type(self), SubscriptionFilter())
        task = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(bus.listener_count, 0)

    async def test_shutdown_and_unstarted_close(self):
        """Even iterators never started by the transport can be cleaned up."""
        bus = InMemoryMcpEventBus()
        unused = bus.listen(type(self), SubscriptionFilter())
        await unused.aclose()
        stream = bus.listen(type(self), SubscriptionFilter())
        await bus.shutdown()
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        self.assertEqual(bus.listener_count, 0)
