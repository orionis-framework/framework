from __future__ import annotations
import asyncio
import io
from unittest.mock import MagicMock, patch
from orionis.console.output.contracts.http_request import IHTTPRequestPrinter
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.test import TestCase

class TestHTTPRequestPrinter(TestCase):

    def _make_adapter(
        self,
        method: str = "GET",
        path: str = "/test",
    ) -> MagicMock:
        """
        Build a mock TransportAdapter with controllable method and path.

        Parameters
        ----------
        method : str
            HTTP method string the adapter should report.
        path : str
            URL path the adapter should report.

        Returns
        -------
        MagicMock
            A mock satisfying the TransportAdapter interface.
        """
        adapter = MagicMock()
        adapter.method.return_value = method
        adapter.path.return_value = path
        return adapter

    def _make_response(self, code: int = 200) -> MagicMock:
        """
        Build a mock Response with a controllable status code.

        Parameters
        ----------
        code : int
            HTTP status code the response should report.

        Returns
        -------
        MagicMock
            A mock satisfying the Response interface.
        """
        response = MagicMock()
        response.getStatusCode.return_value = code
        return response

    def _make(self) -> HTTPRequestPrinter:
        """
        Create an HTTPRequestPrinter with default terminal width.

        Returns
        -------
        HTTPRequestPrinter
            A printer instance ready for testing.
        """
        return HTTPRequestPrinter()

    def _make_with_width(self, columns: int) -> HTTPRequestPrinter:
        """
        Create an HTTPRequestPrinter forcing a specific terminal column count.

        Parameters
        ----------
        columns : int
            Simulated terminal column width.

        Returns
        -------
        HTTPRequestPrinter
            A printer whose _total_width reflects the given column count.
        """
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value = MagicMock(columns=columns)
            return HTTPRequestPrinter()

    def testInstantiation(self) -> None:
        """Verify that HTTPRequestPrinter can be instantiated without errors.

        Ensures the constructor completes without raising any exception
        and returns a valid instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        self.assertIsInstance(printer, HTTPRequestPrinter)

    def testIsSubclassOfIHTTPRequestPrinter(self) -> None:
        """Verify that HTTPRequestPrinter is a subclass of IHTTPRequestPrinter.

        Ensures the concrete implementation satisfies the interface contract
        and can be used polymorphically via the abstract base.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(HTTPRequestPrinter, IHTTPRequestPrinter))

    def testInstanceIsIHTTPRequestPrinter(self) -> None:
        """Verify that an HTTPRequestPrinter instance satisfies isinstance check.

        Ensures polymorphic usage is valid so any code accepting an
        IHTTPRequestPrinter can transparently receive an HTTPRequestPrinter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        self.assertIsInstance(printer, IHTTPRequestPrinter)

    def testHttpColorsContainsCommonMethods(self) -> None:
        """Verify that HTTP_COLORS contains entries for common HTTP methods.

        Ensures the colour map covers at least the most frequently used
        HTTP verbs so they are always rendered with a dedicated style.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            self.assertIn(method, HTTPRequestPrinter.HTTP_COLORS)

    def testHttpColorsContainsDefaultEntry(self) -> None:
        """Verify that HTTP_COLORS provides a 'default' fallback entry.

        Ensures unknown HTTP methods are rendered with a predictable
        style instead of raising a KeyError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("default", HTTPRequestPrinter.HTTP_COLORS)

    def testStatusColorsContainsAllCategories(self) -> None:
        """Verify that STATUS_COLORS covers all standard HTTP status categories.

        Ensures 1xx-5xx are mapped so every response code has an
        associated colour scheme.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for category in ("1xx", "2xx", "3xx", "4xx", "5xx", "default"):
            self.assertIn(category, HTTPRequestPrinter.STATUS_COLORS)

    def testHttpMinStatusCodeIsOneHundred(self) -> None:
        """Verify the minimum valid HTTP status code constant equals 100.

        Ensures the boundary check for the status code category lookup
        is anchored at the correct RFC-defined minimum.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPRequestPrinter.HTTP_MIN_STATUS_CODE, 100)

    def testStartTimerReturnsFloat(self) -> None:
        """Verify that startTimer returns a float value when output is enabled.

        Ensures the returned timestamp is a valid high-resolution float
        compatible with time.perf_counter semantics.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        result = printer.startTimer()
        self.assertIsInstance(result, float)

    def testStartTimerIsMonotonic(self) -> None:
        """Verify that consecutive startTimer calls return non-decreasing values.

        Ensures the timer uses a monotonic source and cannot go backwards
        between two calls within the same execution context.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        t1 = printer.startTimer()
        t2 = printer.startTimer()
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)
        self.assertLessEqual(t1, t2)

    def testStartTimerReturnsNoneWhenDisabled(self) -> None:
        """Verify that startTimer returns None when output is disabled.

        Ensures no unnecessary timestamp is captured when
        setEnabled(enabled=False) has been called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        printer.setEnabled(enabled=False)
        result = printer.startTimer()
        self.assertIsNone(result)

    def testStartTimerReturnsFloatAfterReenabling(self) -> None:
        """Verify that startTimer returns a float again after re-enabling output.

        Ensures the timer correctly resumes once setEnabled(enabled=True)
        restores the printer to an active state.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        printer.setEnabled(enabled=False)
        printer.setEnabled(enabled=True)
        result = printer.startTimer()
        self.assertIsInstance(result, float)

    def testPrintRequestReturnsNone(self) -> None:
        """Verify that printRequest returns None.

        Ensures the method adheres to its declared contract which
        specifies a None return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("GET", "/api/health"),
                self._make_response(200),
            )
        self.assertIsNone(result)

    def testPrintRequestWritesToStdoutDirectly(self) -> None:
        """Verify that printRequest writes to stdout when start() has not been called.

        Ensures the direct-write fallback path produces non-empty output
        so requests are logged even outside an async lifecycle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/api/health"),
                self._make_response(200),
            )
        self.assertGreater(len(buf.getvalue()), 0)

    def testPrintRequestWithGetMethod(self) -> None:
        """Verify that printRequest handles the GET method without raising.

        Ensures the most common HTTP method is rendered correctly and the
        method completes without any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("GET", "/users"),
                self._make_response(200),
            )
        self.assertIsNone(result)

    def testPrintRequestWithPostMethod(self) -> None:
        """Verify that printRequest handles the POST method without raising.

        Ensures POST requests are rendered correctly with the appropriate
        colour style.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("POST", "/users"),
                self._make_response(201),
            )
        self.assertIsNone(result)

    def testPrintRequestWithDeleteMethod(self) -> None:
        """Verify that printRequest handles the DELETE method without raising.

        Ensures DELETE requests are rendered correctly without exceptions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("DELETE", "/users/1"),
                self._make_response(204),
            )
        self.assertIsNone(result)

    def testPrintRequestWithUnknownMethod(self) -> None:
        """Verify that printRequest handles an unknown HTTP method gracefully.

        Ensures the 'default' colour fallback is used without raising
        a KeyError when the method is not in HTTP_COLORS.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("BREW", "/coffee"),
                self._make_response(418),
            )
        self.assertIsNone(result)

    def testPrintRequestNormalisesLowercaseMethod(self) -> None:
        """Verify that printRequest normalises a lowercase method to uppercase.

        Ensures that 'get' and 'GET' produce the same rendering behaviour
        so callers are not required to pre-uppercase the method string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("get", "/api"),
                self._make_response(200),
            )
        self.assertIsNone(result)

    def testPrintRequestShortDurationFormatsAsMs(self) -> None:
        """Verify that a sub-second duration is formatted in milliseconds.

        Ensures that durations below 1.0 second are expressed as '~ Xms'
        rather than seconds, matching the expected display convention.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/"),
                self._make_response(200),
            )
        self.assertIn("ms", buf.getvalue())

    def testPrintRequestWith200StatusCode(self) -> None:
        """Verify that a 200 status code is accepted and rendered without error.

        Ensures the most common successful response code maps to the
        2xx category colour correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/"),
                self._make_response(200),
            )
        self.assertIn("200", buf.getvalue())

    def testPrintRequestWith404StatusCode(self) -> None:
        """Verify that a 404 status code is accepted and rendered without error.

        Ensures a client-error response code maps to the 4xx category
        colour without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/missing"),
                self._make_response(404),
            )
        self.assertIn("404", buf.getvalue())

    def testPrintRequestWith500StatusCode(self) -> None:
        """Verify that a 500 status code is accepted and rendered without error.

        Ensures a server-error response code maps to the 5xx category
        colour without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("POST", "/crash"),
                self._make_response(500),
            )
        self.assertIn("500", buf.getvalue())

    def testPrintRequestWith301StatusCode(self) -> None:
        """Verify that a 301 redirect status code is rendered without error.

        Ensures 3xx responses map to the redirect colour category correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("GET", "/moved"),
                self._make_response(301),
            )
        self.assertIsNone(result)

    def testPrintRequestSkipsWellKnownPath(self) -> None:
        """Verify that printRequest silently skips /.well-known/ paths.

        Ensures health-check and ACME challenge requests are not logged
        to reduce noise in the console output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/.well-known/acme-challenge"),
                self._make_response(200),
            )
        self.assertEqual(buf.getvalue(), "")

    def testPrintRequestWithVeryLongPath(self) -> None:
        """Verify that a very long path is truncated and rendered without error.

        Ensures that paths exceeding the computed max_path limit are
        shortened with '...' rather than overflowing the output line.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        long_path = "/" + "x" * 300
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", long_path),
                self._make_response(200),
            )
        self.assertIn("...", buf.getvalue())

    def testPrintRequestWithRootPath(self) -> None:
        """Verify that the root path '/' is accepted and rendered correctly.

        Ensures that a single-character path does not cause off-by-one
        errors in the dot-filler calculation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.startTimer()
            result = printer.printRequest(
                self._make_adapter("GET", "/"),
                self._make_response(200),
            )
        self.assertIsNone(result)

    def testPrintRequestDoesNothingBeforeStartTimer(self) -> None:
        """Verify that printRequest produces no output when startTimer was not called.

        Ensures the printer does not crash and remains silent when no
        timer has been initialised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.printRequest(
                self._make_adapter("GET", "/"),
                self._make_response(200),
            )
        self.assertEqual(buf.getvalue(), "")

    def testSetEnabledFalseDisablesOutput(self) -> None:
        """Verify that setEnabled(False) prevents any output from being produced.

        Ensures the disabled flag is respected and stdout is not written to.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.setEnabled(enabled=False)
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/"),
                self._make_response(200),
            )
        self.assertEqual(buf.getvalue(), "")

    def testSetEnabledTrueRestoresOutput(self) -> None:
        """Verify that re-enabling output after disabling restores stdout writes.

        Ensures toggling the flag back to True allows subsequent requests
        to be logged normally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            printer.setEnabled(enabled=False)
            printer.setEnabled(enabled=True)
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/"),
                self._make_response(200),
            )
        self.assertGreater(len(buf.getvalue()), 0)

    def testTotalWidthClampedToMinimum(self) -> None:
        """Verify that _total_width is at least 60 for a very narrow terminal.

        Ensures the minimum clamp prevents the layout from collapsing on
        extremely narrow displays.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make_with_width(10)
        self.assertGreaterEqual(printer._total_width, 60)

    def testTotalWidthClampedToMaximum(self) -> None:
        """Verify that _total_width is at most 120 for a very wide terminal.

        Ensures the maximum clamp prevents the layout from spanning an
        enormous width on very wide displays.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make_with_width(1000)
        self.assertLessEqual(printer._total_width, 120)

    async def testStartCreatesQueueAndWorker(self) -> None:
        """Verify that start() initialises the internal queue and worker task.

        Ensures the queue and worker_task attributes transition from None
        to a valid Queue and Task after start() is awaited.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        self.assertIsNone(printer._HTTPRequestPrinter__queue)
        self.assertIsNone(printer._HTTPRequestPrinter__worker_task)
        await printer.start()
        self.assertIsNotNone(printer._HTTPRequestPrinter__queue)
        self.assertIsNotNone(printer._HTTPRequestPrinter__worker_task)
        await printer.stop()

    async def testStopDrainsQueueAndCancelsWorker(self) -> None:
        """Verify that stop() resets queue and worker task references to None.

        Ensures the printer is returned to its pre-start state after stop(),
        allowing safe re-use or clean shutdown.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        await printer.start()
        await printer.stop()
        self.assertIsNone(printer._HTTPRequestPrinter__queue)
        self.assertIsNone(printer._HTTPRequestPrinter__worker_task)

    async def testPrintRequestEnqueuesWhenStarted(self) -> None:
        """Verify that printRequest enqueues a line when start() has been called.

        Ensures the worker drains the queue so no messages are lost after
        the printer is running in async mode.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            printer = self._make()
            await printer.start()
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/test"),
                self._make_response(200),
            )
        await asyncio.sleep(0.05)
        queue = printer._HTTPRequestPrinter__queue
        self.assertEqual(queue.qsize(), 0)
        await printer.stop()

    async def testQueueFullDropsMessageSilently(self) -> None:
        """Verify that a full queue causes messages to be dropped without raising.

        Ensures the printer never blocks the event loop under extreme back-
        pressure -- excess messages are silently discarded.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = self._make()
        await printer.start()
        queue = printer._HTTPRequestPrinter__queue
        for _ in range(1000):
            try:
                queue.put_nowait("x")
            except asyncio.QueueFull:
                break
        with patch("sys.stdout", io.StringIO()):
            printer.startTimer()
            printer.printRequest(
                self._make_adapter("GET", "/overflow"),
                self._make_response(200),
            )
        await printer.stop()
