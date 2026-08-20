import io
from orionis.storage.contracts.stream import IStorageStream
from orionis.storage.stream import AsyncStream
from orionis.test import TestCase

class _RecordingHandle:
    """Binary handle double backed by an in-memory buffer."""

    __slots__ = ("buffer", "closed")

    def __init__(self, data: bytes = b"") -> None:
        self.buffer = io.BytesIO(data)
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        """
        Read up to *size* bytes from the buffer.

        Parameters
        ----------
        size : int
            Maximum number of bytes to read.

        Returns
        -------
        bytes
            Bytes read from the current position.
        """
        return self.buffer.read(size)

    def write(self, data: bytes) -> int:
        """
        Write *data* into the buffer.

        Parameters
        ----------
        data : bytes
            Raw bytes to write.

        Returns
        -------
        int
            Number of bytes written.
        """
        return self.buffer.write(data)

    def seek(self, offset: int, whence: int = 0) -> int:
        """
        Move the buffer position to *offset*.

        Parameters
        ----------
        offset : int
            Target offset relative to *whence*.
        whence : int
            Anchor point of the offset.

        Returns
        -------
        int
            The new absolute position.
        """
        return self.buffer.seek(offset, whence)

    def close(self) -> None:
        """Mark the handle as closed."""
        self.closed = True

class _CountingOpener:
    """Handle factory counting how many times it was invoked."""

    __slots__ = ("calls", "handle")

    def __init__(self, handle: _RecordingHandle) -> None:
        self.handle = handle
        self.calls = 0

    def __call__(self) -> _RecordingHandle:
        """
        Return the stubbed handle and count the invocation.

        Returns
        -------
        _RecordingHandle
            The handle supplied at construction time.
        """
        self.calls += 1
        return self.handle

class _CloseRecorder:
    """Close callback recording the handle state on invocation."""

    __slots__ = ("calls", "states")

    def __init__(self) -> None:
        self.calls = 0
        self.states: list[bool] = []

    def __call__(self, handle: _RecordingHandle) -> None:
        """
        Record the handle state right before it is closed.

        Parameters
        ----------
        handle : _RecordingHandle
            Open handle handed over by the stream.

        Returns
        -------
        None
        """
        self.calls += 1
        self.states.append(handle.closed)

class TestAsyncStream(TestCase):

    def setUp(self) -> None:
        """
        Build a stream over a recording handle before each test.

        Keeps every test isolated with its own buffer and counters.
        """
        self._handle = _RecordingHandle(b"payload")
        self._opener = _CountingOpener(self._handle)
        self._on_close = _CloseRecorder()
        self._stream = AsyncStream(self._opener, self._on_close)

    def testImplementsTheStreamContract(self) -> None:
        """
        Expose the stream through its published contract.

        Validates that drivers can type their return values.
        """
        self.assertIsInstance(self._stream, IStorageStream)

    def testConstructionNeverOpensTheHandle(self) -> None:
        """
        Keep construction free of side effects.

        Validates that the opener runs lazily on first use.
        """
        self.assertEqual(self._opener.calls, 0)

    async def testHandleIsOpenedOnlyOnce(self) -> None:
        """
        Reuse the handle opened on the first operation.

        Validates the lazy-open cache shared by every operation.
        """
        await self._stream.read(1)
        await self._stream.read(1)
        self.assertEqual(self._opener.calls, 1)

    async def testReadReturnsRequestedBytes(self) -> None:
        """
        Read the requested number of bytes from the handle.

        Validates the size argument forwarded to the handle.
        """
        self.assertEqual(await self._stream.read(3), b"pay")

    async def testReadWithoutSizeConsumesEverything(self) -> None:
        """
        Read until the end of the stream by default.

        Validates the default ``-1`` size argument.
        """
        self.assertEqual(await self._stream.read(), b"payload")

    async def testWriteReturnsTheWrittenByteCount(self) -> None:
        """
        Write bytes at the current position of the handle.

        Validates the value returned by the underlying handle.
        """
        await self._stream.seek(0, io.SEEK_END)
        self.assertEqual(await self._stream.write(b"-more"), 5)
        self.assertEqual(self._handle.buffer.getvalue(), b"payload-more")

    async def testSeekReturnsTheNewPosition(self) -> None:
        """
        Move the stream position and report the new offset.

        Validates both the offset and the whence arguments.
        """
        self.assertEqual(await self._stream.seek(3), 3)
        self.assertEqual(await self._stream.seek(0, io.SEEK_END), 7)

    async def testCloseRunsTheCallbackBeforeReleasing(self) -> None:
        """
        Invoke the close callback while the handle is still open.

        Validates that drivers can flush buffered data on close.
        """
        await self._stream.read(1)
        await self._stream.close()
        self.assertEqual(self._on_close.calls, 1)
        self.assertEqual(self._on_close.states, [False])
        self.assertTrue(self._handle.closed)

    async def testCloseDetachesTheHandle(self) -> None:
        """
        Detach the handle once the stream has been closed.

        Validates the internal state after a successful close.
        """
        await self._stream.read(1)
        await self._stream.close()
        self.assertIsNone(self._stream._handle)

    async def testCloseIsIdempotent(self) -> None:
        """
        Turn repeated close calls into harmless no-ops.

        Validates that the callback never runs twice.
        """
        await self._stream.read(1)
        await self._stream.close()
        await self._stream.close()
        self.assertEqual(self._on_close.calls, 1)

    async def testCloseWithoutOpeningIsNoOp(self) -> None:
        """
        Skip every action when the handle was never opened.

        Validates the early return of close().
        """
        await self._stream.close()
        self.assertEqual(self._opener.calls, 0)
        self.assertEqual(self._on_close.calls, 0)
        self.assertFalse(self._handle.closed)

    async def testCloseWithoutCallbackReleasesTheHandle(self) -> None:
        """
        Release the handle when no close callback is configured.

        Validates the optional nature of the callback.
        """
        handle = _RecordingHandle(b"x")
        stream = AsyncStream(_CountingOpener(handle))
        await stream.read(1)
        await stream.close()
        self.assertTrue(handle.closed)

    async def testAsyncContextManagerOpensAndReturnsItself(self) -> None:
        """
        Open the handle on entry and yield the stream itself.

        Validates the async context-manager protocol.
        """
        async with self._stream as entered:
            self.assertIs(entered, self._stream)
            self.assertEqual(self._opener.calls, 1)
        self.assertTrue(self._handle.closed)

    async def testAsyncContextManagerClosesOnFailure(self) -> None:
        """
        Close the stream when the guarded block raises.

        Validates the cleanup guarantees of __aexit__.
        """
        error_msg = "boom"
        with self.assertRaises(RuntimeError):
            async with self._stream:
                raise RuntimeError(error_msg)
        self.assertTrue(self._handle.closed)
        self.assertEqual(self._on_close.calls, 1)
