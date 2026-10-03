import asyncio
from dataclasses import FrozenInstanceError
from types import MappingProxyType
from typing import TYPE_CHECKING
from orionis.background.task import BackgroundTask
from orionis.http import EventStreamResponse, ServerSentEvent, response
from orionis.http.factory import ResponseFactory
from orionis.http.responses import StreamingResponse
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

class _AsyncEvents:
    """Record lazy source iteration and deterministic asynchronous cleanup."""

    __slots__ = ("closed", "iterator_calls", "values")

    def __init__(self, values: tuple[object, ...] = ("first",)) -> None:
        """Store source values and reset lifecycle counters.

        Parameters
        ----------
        values : tuple[object, ...], optional
            Values yielded by the asynchronous iterator.

        Returns
        -------
        None
            Initialize the source and its lifecycle counters.
        """
        self.values = iter(values)
        self.closed = 0
        self.iterator_calls = 0

    def __aiter__(self) -> _AsyncEvents:
        """Record iterator creation and return the source itself.

        Returns
        -------
        _AsyncEvents
            This asynchronous iterator.
        """
        self.iterator_calls += 1
        return self

    async def __anext__(self) -> object:
        """Yield the next stored value without prefetching.

        Returns
        -------
        object
            The next stored value.

        Raises
        ------
        StopAsyncIteration
            If no values remain.
        """
        try:
            return next(self.values)
        except StopIteration:
            raise StopAsyncIteration from None

    async def aclose(self) -> None:
        """Count explicit cleanup requests.

        Returns
        -------
        None
            Increment the source cleanup counter.
        """
        self.closed += 1

class _FailingIterable(_AsyncEvents):
    """Fail when creating an iterator to exercise unstarted-source cleanup."""

    __slots__ = ()

    def __aiter__(self) -> _AsyncEvents:
        """Raise before an iterator can be attached to the response.

        Raises
        ------
        RuntimeError
            Always, to exercise cleanup after iterator creation fails.
        """
        error_msg = "cannot create iterator"
        raise RuntimeError(error_msg)

class _ClosingEvents(_AsyncEvents):
    """Suspend asynchronous cleanup until a test permits completion."""

    __slots__ = ("close_error", "finished", "release", "started")

    def __init__(self, close_error: Exception | None = None) -> None:
        """Prepare deterministic cleanup coordination events.

        Parameters
        ----------
        close_error : Exception or None, optional
            Failure to raise after cleanup is released.

        Returns
        -------
        None
            Initialize the cleanup gates and optional failure.
        """
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = asyncio.Event()
        self.close_error = close_error

    async def aclose(self) -> None:
        """Hold cleanup open until the test releases it.

        Raises
        ------
        Exception
            The configured cleanup failure, if provided.
        """
        self.closed += 1
        self.started.set()
        await self.release.wait()
        self.finished.set()
        if self.close_error is not None:
            raise self.close_error

class TestServerSentEvent(TestCase):

    def testEncodesIndividualFields(self) -> None:
        """Encode each field with exact LF framing and no implicit payload.

        Returns
        -------
        None
            Verify each individual event field's encoded frame.
        """
        cases = (
            (ServerSentEvent(data="hello"), b"data: hello\n\n"),
            (ServerSentEvent(event="message"), b"event: message\n\n"),
            (ServerSentEvent(id="42"), b"id: 42\n\n"),
            (ServerSentEvent(retry=1500), b"retry: 1500\n\n"),
            (ServerSentEvent(retry=0), b"retry: 0\n\n"),
            (ServerSentEvent(comment="ping"), b": ping\n\n"),
            (ServerSentEvent(), b"\n\n"),
        )
        for event, expected in cases:
            with self.subTest(event=event):
                self.assertEqual(event.encode(), expected)

    def testEncodesCombinedFieldsInStableOrder(self) -> None:
        """Emit comments, metadata and data within a single event frame.

        Returns
        -------
        None
            Verify the field order and exact combined frame.
        """
        event = ServerSentEvent(
            data="ready", event="connected", id="1", retry=500, comment="ping",
        )
        self.assertEqual(
            event.encode(),
            b": ping\nevent: connected\nid: 1\nretry: 500\ndata: ready\n\n",
        )

    def testNormalizesDataNewlinesAndPreservesTrailingEmptyData(self) -> None:
        """Normalize CR and CRLF while prefixing every payload line.

        Returns
        -------
        None
            Verify normalized payload lines and trailing empty data.
        """
        event = ServerSentEvent(data="first\r\nsecond\rthird\n")
        self.assertEqual(
            event.encode(), b"data: first\ndata: second\ndata: third\ndata: \n\n",
        )

    def testNormalizesCommentNewlines(self) -> None:
        """Prefix every normalized comment line, including the final empty one.

        Returns
        -------
        None
            Verify every comment line receives its SSE prefix.
        """
        event = ServerSentEvent(comment="first\r\nsecond\rthird\n")
        self.assertEqual(event.encode(), b": first\n: second\n: third\n: \n\n")

    def testPreservesNonSseUnicodeSeparators(self) -> None:
        """Keep Unicode line separators in the payload instead of splitting them.

        Returns
        -------
        None
            Verify non-SSE Unicode separators remain unchanged.
        """
        data = "left\u2028middle\u2029right\vfinal"
        self.assertEqual(
            ServerSentEvent(data=data).encode(), f"data: {data}\n\n".encode(),
        )

    def testEncodesUnicodeAsUtf8(self) -> None:
        """Encode non-ASCII text as UTF-8 without escaping it.

        Returns
        -------
        None
            Verify event fields preserve their Unicode text in UTF-8.
        """
        event = ServerSentEvent(data="¡Hola 世界! 🌍", event="aviso", id="é")
        self.assertEqual(
            event.encode(), "event: aviso\nid: é\ndata: ¡Hola 世界! 🌍\n\n".encode(),
        )

    def testEmptyStringsRemainExplicitFields(self) -> None:
        """Distinguish empty field values from omitted fields.

        Returns
        -------
        None
            Verify explicitly empty fields are encoded.
        """
        event = ServerSentEvent(data="", event="", id="", comment="")
        self.assertEqual(event.encode(), b": \nevent: \nid: \ndata: \n\n")

    def testRejectsLineInjectionInEventAndId(self) -> None:
        """Reject CR and LF in metadata before any bytes are emitted.

        Returns
        -------
        None
            Verify invalid event names and IDs raise ValueError.
        """
        for field in ("event", "id"):
            for value in ("first\nsecond", "first\rsecond", "first\r\nsecond"):
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(ValueError),
                ):
                    ServerSentEvent(**{field: value})

    def testRejectsNulInId(self) -> None:
        """Reject cursor values that an SSE client would otherwise ignore.

        Returns
        -------
        None
            Verify NUL characters are rejected in event IDs.
        """
        with self.assertRaises(ValueError):
            ServerSentEvent(id="before\0after")

    def testRejectsInvalidTextFieldTypes(self) -> None:
        """Require actual strings without implicit JSON or string conversion.

        Returns
        -------
        None
            Verify non-string event fields raise TypeError.
        """
        for field in ("data", "event", "id", "comment"):
            for value in (1, False, b"bytes", {}, [], object()):
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(TypeError),
                ):
                    ServerSentEvent(**{field: value})

    def testRejectsInvalidRetryTypes(self) -> None:
        """Reject booleans, fractional numbers and textual retry delays.

        Returns
        -------
        None
            Verify invalid retry values raise TypeError.
        """
        for value in (True, False, 1.0, "1000", b"1000", object()):
            with self.subTest(value=value), self.assertRaises(TypeError):
                ServerSentEvent(retry=value)

    def testRejectsNegativeRetry(self) -> None:
        """Reject negative reconnection delays at construction time.

        Returns
        -------
        None
            Verify a negative retry value raises ValueError.
        """
        with self.assertRaises(ValueError):
            ServerSentEvent(retry=-1)

    def testEventIsImmutableAndSlotted(self) -> None:
        """Prevent mutable fields or ad hoc state on an event value.

        Returns
        -------
        None
            Verify immutability and the absence of an instance dictionary.
        """
        event = ServerSentEvent(data="stable")
        with self.assertRaises(FrozenInstanceError):
            event.data = "changed"
        self.assertFalse(hasattr(event, "__dict__"))

class TestEventStreamResponse(TestCase):

    async def asyncSetUp(self) -> None:
        """Capture unexpected event-loop errors during stream lifecycle tests.

        Returns
        -------
        None
            Install a loop exception handler for the current test.
        """
        self.loop = asyncio.get_running_loop()
        self.previous_handler = self.loop.get_exception_handler()
        self.loop_errors = []
        self.loop.set_exception_handler(self.recordLoopError)

    async def asyncTearDown(self) -> None:
        """Restore loop reporting and reject unhandled cleanup exceptions.

        Returns
        -------
        None
            Restore the previous loop handler and verify no errors were logged.
        """
        await asyncio.sleep(0)
        self.loop.set_exception_handler(self.previous_handler)
        self.assertEqual(self.loop_errors, [])

    def recordLoopError(
        self, _loop: asyncio.AbstractEventLoop, context: dict,
    ) -> None:
        """Retain unexpected background errors for the teardown assertion.

        Parameters
        ----------
        _loop : asyncio.AbstractEventLoop
            Event loop reporting the error.
        context : dict
            Error details supplied by the loop.

        Returns
        -------
        None
            Append the error context for teardown verification.
        """
        self.loop_errors.append(context)

    def testUsesExistingStreamingResponse(self) -> None:
        """Keep SSE on the existing streaming response and contract hierarchy.

        Returns
        -------
        None
            Verify response inheritance, stream presence, and instance layout.
        """
        result = EventStreamResponse([])
        self.assertIsInstance(result, StreamingResponse)
        self.assertTrue(result.hasStream())
        self.assertIsNone(result.getBody())
        self.assertFalse(hasattr(result, "__dict__"))

    def testProvidesSseHeadersWithoutHopByHopHeaders(self) -> None:
        """Advertise UTF-8 events and disable buffering without fixed length.

        Returns
        -------
        None
            Verify default SSE headers and omitted hop-by-hop headers.
        """
        result = EventStreamResponse([])
        self.assertEqual(result.getStringHeaders(), [
            ("content-type", "text/event-stream; charset=utf-8"),
            ("cache-control", "no-cache"),
            ("x-accel-buffering", "no"),
        ])
        self.assertFalse(result.hasHeader("connection"))
        self.assertFalse(result.hasHeader("content-length"))

    def testPreservesExplicitHeadersWithoutMutatingTheirMapping(self) -> None:
        """Respect case-insensitive overrides and discard an invalid fixed length.

        Returns
        -------
        None
            Verify explicit headers are preserved without mutating their source.
        """
        headers = MappingProxyType({
            "Content-Type": "text/event-stream; custom=true",
            "Cache-Control": "private, no-store",
            "X-Accel-Buffering": "yes",
            "Content-Length": "100",
            "X-Application": "events",
        })
        result = EventStreamResponse([], status_code=201, headers=headers)
        self.assertEqual(result.getStatusCode(), 201)
        self.assertEqual(result.getHeader("content-type"), [headers["Content-Type"]])
        self.assertEqual(result.getHeader("cache-control"), ["private, no-store"])
        self.assertEqual(result.getHeader("x-accel-buffering"), ["yes"])
        self.assertEqual(result.getHeader("x-application"), ["events"])
        self.assertFalse(result.hasHeader("content-length"))
        self.assertEqual(headers["Content-Length"], "100")

    def testNeverSerializesLaterContentLengthMutations(self) -> None:
        """Prevent middleware or fluent header mutations from fixing stream length.

        Returns
        -------
        None
            Verify content length remains absent after header mutations.
        """
        result = EventStreamResponse([])
        result.setHeader("Content-Length", "100")
        result.addHeader("CONTENT-LENGTH", "200")
        self.assertNotIn("content-length", dict(result.getStringHeaders()))
        self.assertNotIn(b"content-length", dict(result.getRawHeaders()))

    async def testEncodesSynchronousEventsAndStringsLazily(self) -> None:
        """Consume exactly one event for each requested byte frame.

        Returns
        -------
        None
            Verify synchronous sources are consumed one event at a time.
        """
        consumed = []

        def events() -> Iterator[ServerSentEvent | str]:
            """Record pulls from the synchronous event source.

            Yields
            ------
            ServerSentEvent or str
                Each event requested by the stream adapter.
            """
            consumed.append("first")
            yield "hello"
            consumed.append("second")
            yield ServerSentEvent(data="ready", event="status")

        stream = aiter(EventStreamResponse(events()).getStream())
        self.assertEqual(consumed, [])
        self.assertEqual(await anext(stream), b"data: hello\n\n")
        self.assertEqual(consumed, ["first"])
        self.assertEqual(await anext(stream), b"event: status\ndata: ready\n\n")
        self.assertEqual(consumed, ["first", "second"])
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)
        await stream.aclose()

    async def testEncodesAsynchronousEventsAndStrings(self) -> None:
        """Adapt an async generator into UTF-8 frames without buffering.

        Returns
        -------
        None
            Verify asynchronous event values are encoded as expected.
        """
        async def events() -> AsyncIterator[ServerSentEvent | str]:
            """Yield a text event and a manual heartbeat.

            Yields
            ------
            ServerSentEvent or str
                Encodable event values in source order.
            """
            yield "first\nsecond"
            yield ServerSentEvent(comment="ping")

        stream = aiter(EventStreamResponse(events()).getStream())
        self.assertEqual(
            [chunk async for chunk in stream],
            [b"data: first\ndata: second\n\n", b": ping\n\n"],
        )
        await stream.aclose()

    async def testTextEventsMatchStructuredFraming(self) -> None:
        """Keep raw text equivalent to event data across both source protocols.

        Returns
        -------
        None
            Verify raw text and structured data produce identical frames.
        """
        values = (
            "", "plain", "\n", "\r", "\r\n", "first\r\nsecond\rthird\n",
            "\n\nlast\n", "left\u2028middle\u2029right\vfinal", "nul\0value",
            "\u00e9\u4e16\u754c",
        )
        expected = [ServerSentEvent(data=value).encode() for value in values]
        for source in (values, _AsyncEvents(values)):
            with self.subTest(source=type(source).__name__):
                stream = aiter(EventStreamResponse(source).getStream())
                try:
                    self.assertEqual([chunk async for chunk in stream], expected)
                finally:
                    await stream.aclose()

    def testRejectsNonIterableSources(self) -> None:
        """Reject unsupported event sources before returning a response.

        Returns
        -------
        None
            Verify invalid source objects raise TypeError.
        """
        for value in (None, 1, object()):
            with self.subTest(value=value), self.assertRaises(TypeError):
                EventStreamResponse(value)

    async def testRejectsInvalidItemsOnlyWhenIterated(self) -> None:
        """Reject unsupported values at the offending item without prefetching.

        Returns
        -------
        None
            Verify invalid source items fail only when requested.
        """
        for value in (b"raw", 1, {}, None, object()):
            for asynchronous in (False, True):
                with self.subTest(value=value, asynchronous=asynchronous):
                    source = _AsyncEvents((value,)) if asynchronous else [value]
                    stream = aiter(EventStreamResponse(source).getStream())
                    with self.assertRaises(TypeError):
                        await anext(stream)
                    await stream.aclose()

    async def testClosesUnstartedSourceWithoutRequestingItsIterator(self) -> None:
        """Release source ownership on an early transport failure or HEAD.

        Returns
        -------
        None
            Verify an unstarted source closes without creating its iterator.
        """
        source = _AsyncEvents()
        stream = aiter(EventStreamResponse(source).getStream())
        self.assertEqual(source.iterator_calls, 0)
        await stream.aclose()
        await stream.aclose()
        self.assertEqual(source.iterator_calls, 0)
        self.assertEqual(source.closed, 1)
        with self.assertRaises(StopAsyncIteration):
            await anext(stream)

    async def testClosesSourceAfterIteratorCreationFails(self) -> None:
        """Keep ownership when a source raises from its __aiter__ method.

        Returns
        -------
        None
            Verify the source closes after iterator creation fails.
        """
        source = _FailingIterable()
        stream = aiter(EventStreamResponse(source).getStream())
        with self.assertRaisesRegex(RuntimeError, "cannot create iterator"):
            await anext(stream)
        await stream.aclose()
        self.assertEqual(source.closed, 1)

    async def testClosesAsynchronousSourceExactlyOnce(self) -> None:
        """Close an iterator once after successful consumption and release it.

        Returns
        -------
        None
            Verify the source closes once and references are released.
        """
        source = _AsyncEvents()
        stream = aiter(EventStreamResponse(source).getStream())
        self.assertEqual([chunk async for chunk in stream], [b"data: first\n\n"])
        await stream.aclose()
        await stream.aclose()
        self.assertEqual(source.closed, 1)
        self.assertIsNone(stream._source)
        self.assertIsNone(stream._iterator)

    async def testClosesDistinctIteratorOwnedByIterable(self) -> None:
        """Close the returned iterator when the source is a separate container.

        Returns
        -------
        None
            Verify that the distinct iterator is closed exactly once.
        """
        source = _AsyncEvents()

        class Events:
            __slots__ = ()

            def __aiter__(self) -> _AsyncEvents:
                """Return the externally observed iterator.

                Returns
                -------
                _AsyncEvents
                    Iterator exposed by the enclosing test.
                """
                return source

        stream = aiter(EventStreamResponse(Events()).getStream())
        self.assertEqual(await anext(stream), b"data: first\n\n")
        await stream.aclose()
        self.assertEqual(source.closed, 1)

    async def testClosesSynchronousGenerator(self) -> None:
        """Run synchronous generator finalizers on early stream termination.

        Returns
        -------
        None
            Verify early stream closure runs the generator finalizer once.
        """
        finalized = []

        def events() -> Iterator[str]:
            """Record generator cleanup without consuming subsequent events.

            Yields
            ------
            str
                Event values available before the stream is closed.
            """
            try:
                yield "first"
                yield "second"
            finally:
                finalized.append("closed")

        stream = aiter(EventStreamResponse(events()).getStream())
        self.assertEqual(await anext(stream), b"data: first\n\n")
        await stream.aclose()
        await stream.aclose()
        self.assertEqual(finalized, ["closed"])

    async def testWaitsForCleanupThroughRepeatedCancellation(self) -> None:
        """Join the owned cleanup task before propagating repeated cancellation.

        Returns
        -------
        None
            Verify repeated cancellation waits for cleanup completion.
        """
        source = _ClosingEvents()
        stream = aiter(EventStreamResponse(source).getStream())
        closing = asyncio.create_task(stream.aclose())
        await source.started.wait()
        closing.cancel()
        await asyncio.sleep(0)
        closing.cancel()
        await asyncio.sleep(0)
        self.assertFalse(closing.done())
        source.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await closing
        self.assertTrue(source.finished.is_set())
        self.assertEqual(source.closed, 1)
        self.assertIsNone(stream._close_task)
        await stream.aclose()
        self.assertEqual(source.closed, 1)

    async def testConcurrentCloseCallsShareOneCleanup(self) -> None:
        """Wait for the same producer finalizer when cleanup callers overlap.

        Returns
        -------
        None
            Verify concurrent close calls share one cleanup operation.
        """
        source = _ClosingEvents()
        stream = aiter(EventStreamResponse(source).getStream())
        first = asyncio.create_task(stream.aclose())
        await source.started.wait()
        second = asyncio.create_task(stream.aclose())
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        source.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(source.closed, 1)

    async def testPropagatesCleanupErrors(self) -> None:
        """Expose producer close failures without retrying a completed cleanup.

        Returns
        -------
        None
            Verify cleanup failures propagate and completed cleanup is not retried.
        """
        failure = RuntimeError("close failed")
        source = _ClosingEvents(failure)
        source.release.set()
        stream = aiter(EventStreamResponse(source).getStream())
        with self.assertRaises(RuntimeError) as caught:
            await stream.aclose()
        self.assertIs(caught.exception, failure)
        await stream.aclose()
        self.assertEqual(source.closed, 1)

    async def testPropagatesCleanupFailureDuringCancellation(self) -> None:
        """Keep a close failure visible when cancellation arrives during cleanup.

        Returns
        -------
        None
            Verify cleanup failure remains visible with cancellation as its cause.
        """
        failure = RuntimeError("close failed")
        source = _ClosingEvents(failure)
        stream = aiter(EventStreamResponse(source).getStream())
        closing = asyncio.create_task(stream.aclose())
        await source.started.wait()
        closing.cancel()
        source.release.set()
        with self.assertRaises(RuntimeError) as caught:
            await closing
        self.assertIs(caught.exception, failure)
        self.assertIsInstance(caught.exception.__cause__, asyncio.CancelledError)
        self.assertEqual(source.closed, 1)

class TestEventStreamFactory(TestCase):

    async def testFactoryForwardsArgumentsAndDefersBackground(self) -> None:
        """Use the public factory with the existing response options.

        Returns
        -------
        None
            Verify factory options are forwarded and background work is deferred.
        """
        calls = []
        task = BackgroundTask(calls.append, "done")
        result = response.eventStream(
            [ServerSentEvent(data="ready")],
            status_code=201,
            headers={"X-Source": "factory"},
            background=task,
        )
        self.assertIsInstance(result, EventStreamResponse)
        self.assertIsInstance(response, ResponseFactory)
        self.assertEqual(result.getStatusCode(), 201)
        self.assertEqual(result.getHeader("x-source"), ["factory"])
        self.assertIs(result.background, task)
        stream = aiter(result.getStream())
        self.assertEqual([chunk async for chunk in stream], [b"data: ready\n\n"])
        await stream.aclose()
        self.assertEqual(calls, [])

    def testPublicExportsResolveToTheirDefiningClasses(self) -> None:
        """Expose SSE through the existing lazy HTTP package export pattern.

        Returns
        -------
        None
            Verify package exports reference the defining response and event types.
        """
        from orionis.http.responses import EventStreamResponse as DefinedResponse
        from orionis.http.sse import ServerSentEvent as DefinedEvent

        self.assertIs(EventStreamResponse, DefinedResponse)
        self.assertIs(ServerSentEvent, DefinedEvent)
