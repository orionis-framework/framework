import io
import os
import sys
import threading
import unittest
from unittest.mock import patch
from orionis.console.startup import startup_feedback, stop_startup_feedback

_FRAME = "⠋ Inicializando Orionis..."
_CLEAR = "\r" + " " * len(_FRAME) + "\r"

class _BinaryStream(io.BytesIO):

    def __init__(self, events: list[tuple[str, str | bytes]], name: str) -> None:
        """
        Initialize a byte buffer that records writes in a shared log.

        Parameters
        ----------
        events : list[tuple[str, str | bytes]]
            Shared output log to update on each write.
        name : str
            Stream label to record alongside each value.

        Returns
        -------
        None
            Initialize an empty buffer and retain the log and stream label.
        """
        super().__init__()
        self.events = events
        self.name = name

    def write(self, value: bytes) -> int:
        """
        Record binary output and write it to the buffer.

        Parameters
        ----------
        value : bytes
            Bytes to record and write unchanged.

        Returns
        -------
        int
            Number of bytes written to the buffer.
        """
        self.events.append((self.name, value))
        return super().write(value)

class _Terminal(io.StringIO):

    def __init__(
        self, events: list[tuple[str, str | bytes]], name: str,
        *, terminal: bool = True, encoding: str = "utf-8",
    ) -> None:
        """
        Initialize a text stream with configurable terminal metadata.

        Parameters
        ----------
        events : list[tuple[str, str | bytes]]
            Shared log for text and binary writes.
        name : str
            Stream label to record alongside each value.
        terminal : bool, optional
            Terminal status reported by ``isatty``. Default is ``True``.
        encoding : str, optional
            Encoding label exposed by the stream. Default is ``"utf-8"``.

        Returns
        -------
        None
            Initialize text and binary buffers with shared output recording.
        """
        super().__init__()
        self.events = events
        self.name = name
        self.terminal = terminal
        self._encoding = encoding
        self.buffer = _BinaryStream(events, name)

    @property
    def encoding(self) -> str:
        """
        Return the configured encoding label without converting data.

        Returns
        -------
        str
            Encoding label supplied when the stream was initialized.
        """
        return self._encoding

    def fileno(self) -> int:
        """
        Return the synthetic descriptor used for terminal-size checks.

        Returns
        -------
        int
            Fixed descriptor ``42`` used with the mocked terminal query.
        """
        return 42

    def isatty(self) -> bool:
        """
        Return the configured terminal status.

        Returns
        -------
        bool
            Whether the stream should be treated as an interactive terminal.
        """
        return self.terminal

    def write(self, value: str) -> int:
        """
        Record text output and write it to the buffer.

        Parameters
        ----------
        value : str
            Text to record and write unchanged.

        Returns
        -------
        int
            Number of characters written to the buffer.
        """
        self.events.append((self.name, value))
        return super().write(value)

class TestStartupFeedback(unittest.TestCase):

    def setUp(self) -> None:
        """
        Create interactive streams and isolate terminal detection.

        Returns
        -------
        None
            Install stream and environment patches with automatic cleanup.
        """
        self.events: list[tuple[str, str | bytes]] = []
        self.stdout = _Terminal(self.events, "stdout")
        self.stderr = _Terminal(self.events, "stderr")
        self.enterContext(patch.object(sys, "stdout", self.stdout))
        self.enterContext(patch.object(sys, "stderr", self.stderr))
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch(
            "orionis.console.startup.os.get_terminal_size",
            return_value=os.terminal_size((80, 24)),
        ))

    def testAppearsBeforeBootstrapAndClearsBeforeFirstStdout(self) -> None:
        """
        Verify that feedback appears immediately and clears before stdout.

        Returns
        -------
        None
            Assert display order, unchanged ANSI output, and stream restoration.
        """
        with startup_feedback(["reactor", "list"]):
            self.assertEqual(self.events, [("stderr", _FRAME)])
            self.assertIsNot(sys.stdout, self.stdout)
            self.assertEqual(sys.stdout.write("\x1b[32mRUNNING\x1b[0m\n"), 17)
            self.assertIs(sys.stdout, self.stdout)
            self.assertIs(sys.stderr, self.stderr)
        self.assertEqual(self.events, [
            ("stderr", _FRAME), ("stderr", _CLEAR),
            ("stdout", "\x1b[32mRUNNING\x1b[0m\n"),
        ])

    def testClearsBeforeFirstStderrAndPreservesProgress(self) -> None:
        """
        Verify that stderr output clears feedback before progress updates.

        Returns
        -------
        None
            Assert preserved carriage returns and subsequent progress text.
        """
        with startup_feedback(["reactor", "long-command"]):
            sys.stderr.write("\rprogress 1")
            sys.stderr.write("\rprogress 2\n")
        self.assertEqual(
            self.stderr.getvalue(), _FRAME + _CLEAR + "\rprogress 1\rprogress 2\n",
        )

    def testEmptyWritesAndFlushDoNotRetireFeedback(self) -> None:
        """
        Verify that empty writes and flushing leave feedback active.

        Returns
        -------
        None
            Assert that text and binary no-op writes preserve the proxy.
        """
        with startup_feedback(["reactor", "list"]):
            proxy = sys.stdout
            self.assertEqual(proxy.write(""), 0)
            self.assertEqual(proxy.buffer.write(b""), 0)
            proxy.flush()
            proxy.writelines([])
            self.assertIs(sys.stdout, proxy)
        self.assertEqual(self.stderr.getvalue(), _FRAME + _CLEAR)

    def testSilentCommandClearsAndRestoresOnExit(self) -> None:
        """
        Verify that a silent command clears feedback when its context exits.

        Returns
        -------
        None
            Assert restored streams and cleanup without an added newline.
        """
        with startup_feedback(["reactor", "silent"]):
            pass
        self.assertIs(sys.stdout, self.stdout)
        self.assertIs(sys.stderr, self.stderr)
        self.assertEqual(self.stderr.getvalue(), _FRAME + _CLEAR)
        self.assertNotIn("\n", self.stderr.getvalue())

    def testErrorsAndInterruptsCleanUpWithoutChangingException(self) -> None:
        """
        Verify cleanup without replacing exceptions or interruption objects.

        Returns
        -------
        None
            Assert exception identity and stream restoration in every case.
        """
        for error in (RuntimeError("bootstrap"), KeyboardInterrupt(), SystemExit(23)):
            with self.subTest(error=type(error).__name__):
                with (
                    self.assertRaises(type(error)) as raised,
                    startup_feedback(["reactor", "fail"]),
                ):
                    raise error
                self.assertIs(raised.exception, error)
                self.assertIs(sys.stdout, self.stdout)
                self.assertIs(sys.stderr, self.stderr)
        self.assertEqual(self.stderr.getvalue(), (_FRAME + _CLEAR) * 3)

    def testBinaryWritesClearBeforeForwardingUnchangedBytes(self) -> None:
        """
        Verify that binary writes clear feedback before forwarding bytes.

        Returns
        -------
        None
            Assert cleanup order and unchanged payloads on both binary streams.
        """
        for name, stream in (("stdout", self.stdout), ("stderr", self.stderr)):
            with self.subTest(stream=name):
                self.events.clear()
                with startup_feedback(["reactor", "binary"]):
                    writer = getattr(sys, name).buffer
                    self.assertEqual(writer.write(b"\x1b[32m\xff\r\n"), 8)
                self.assertEqual(self.events, [
                    ("stderr", _FRAME), ("stderr", _CLEAR),
                    (name, b"\x1b[32m\xff\r\n"),
                ])
                self.assertTrue(stream.buffer.getvalue().endswith(b"\x1b[32m\xff\r\n"))

    def testCachedProxiesRemainUsableAfterCleanup(self) -> None:
        """
        Verify that captured text and binary proxies remain usable after cleanup.

        Returns
        -------
        None
            Assert later line writes reach the original buffers unchanged.
        """
        with startup_feedback(["reactor", "list"]):
            writer = sys.stdout
            binary = writer.buffer
        writer.writelines(["one", "two\n"])
        binary.writelines([b"three", b"four\n"])
        self.assertEqual(self.stdout.getvalue(), "onetwo\n")
        self.assertEqual(self.stdout.buffer.getvalue(), b"threefour\n")
        self.assertEqual(self.stderr.getvalue(), _FRAME + _CLEAR)

    def testDelegatesStreamMetadataAndDoesNotInventBuffer(self) -> None:
        """
        Verify stream metadata delegation and missing-buffer behavior.

        Returns
        -------
        None
            Assert delegated attributes and an error when no binary buffer exists.
        """
        with startup_feedback(["reactor", "list"]):
            self.assertEqual(sys.stdout.fileno(), self.stdout.fileno())
            self.assertEqual(sys.stdout.encoding, self.stdout.encoding)
            self.assertTrue(sys.stdout.isatty())
            self.assertFalse(sys.stdout.closed)
            self.assertTrue(sys.stdout.writable())
            del self.stderr.buffer
            with self.assertRaises(AttributeError):
                _ = sys.stderr.buffer

    def testRedirectedStdoutOrStderrSkipsFeedback(self) -> None:
        """
        Verify that redirecting either standard stream disables feedback.

        Returns
        -------
        None
            Assert original streams remain installed without output events.
        """
        for stream in (self.stdout, self.stderr):
            with self.subTest(stream=stream.name):
                stream.terminal = False
                with startup_feedback(["reactor", "list"]):
                    self.assertIs(sys.stdout, self.stdout)
                    self.assertIs(sys.stderr, self.stderr)
                stream.terminal = True
        self.assertEqual(self.events, [])

    def testCiAndDumbTerminalsSkipFeedback(self) -> None:
        """
        Verify that CI and dumb terminals disable interactive feedback.

        Returns
        -------
        None
            Assert no feedback for CI values or a dumb terminal setting.
        """
        for environment in ({"CI": "true"}, {"CI": ""}, {"TERM": "dumb"}):
            with (
                self.subTest(environment=environment),
                patch.dict(os.environ, environment),
                startup_feedback(["reactor", "list"]),
            ):
                self.assertIs(sys.stdout, self.stdout)
        self.assertEqual(self.events, [])

    def testMcpProtocolAlwaysSkipsFeedback(self) -> None:
        """
        Verify that MCP startup remains free of feedback output.

        Returns
        -------
        None
            Assert executable tokens and paths do not enable protocol feedback.
        """
        for arguments in (
            ["mcp:start"], ["reactor", "mcp:start"],
            ["C:\\project\\reactor.py", "mcp:start"],
        ):
            with self.subTest(arguments=arguments), startup_feedback(arguments):
                self.assertIs(sys.stdout, self.stdout)
        self.assertEqual(self.events, [])

    def testFallsBackToAsciiWithoutChangingEncoding(self) -> None:
        """
        Verify the ASCII fallback without changing the stream encoding.

        Returns
        -------
        None
            Assert an encodable message, matching cleanup, and unchanged encoding.
        """
        self.stderr._encoding = "ascii"
        with startup_feedback(["reactor", "list"]):
            sys.stdout.write("command\n")
        frame = "- Inicializando Orionis..."
        self.assertEqual(self.stderr.getvalue(), frame + "\r" + " " * len(frame) + "\r")
        self.assertEqual(self.stderr.encoding, "ascii")

    def testNarrowTerminalSkipsFeedbackInsteadOfWrapping(self) -> None:
        """
        Verify that insufficient terminal width disables feedback.

        Returns
        -------
        None
            Assert no message when its length equals the available columns.
        """
        with patch(
            "orionis.console.startup.os.get_terminal_size",
            return_value=os.terminal_size((len(_FRAME), 24)),
        ), startup_feedback(["reactor", "list"]):
            self.assertIs(sys.stdout, self.stdout)
        self.assertEqual(self.events, [])

    def testNestedContextsKeepOneMessage(self) -> None:
        """
        Verify that nested startup contexts share one feedback message.

        Returns
        -------
        None
            Assert proxy reuse and exactly one displayed message and cleanup.
        """
        with startup_feedback(["reactor", "list"]):
            writer = sys.stdout
            with startup_feedback(["reactor", "list"]):
                self.assertIs(sys.stdout, writer)
                sys.stdout.write("command\n")
        self.assertEqual(self.stderr.getvalue(), _FRAME + _CLEAR)

    def testConcurrentFirstWritesClearExactlyOnce(self) -> None:
        """
        Verify that concurrent first writes clear feedback exactly once.

        Returns
        -------
        None
            Assert cleanup precedes both worker messages and all workers finish.
        """
        with startup_feedback(["reactor", "list"]):
            stdout, stderr = sys.stdout, sys.stderr
            ready = threading.Barrier(3)

            def output(writer: object, message: str) -> None:
                """
                Write a message after synchronizing the worker threads.

                Parameters
                ----------
                writer : object
                    Captured stdout or stderr proxy that receives the message.
                message : str
                    Text to write once all barrier participants are ready.

                Returns
                -------
                None
                    Wait at the shared barrier and forward the message.
                """
                ready.wait()
                writer.write(message)

            workers = [
                threading.Thread(target=output, args=(stdout, "one\n")),
                threading.Thread(target=output, args=(stderr, "two\n")),
            ]
            for worker in workers:
                worker.start()
            ready.wait()
            for worker in workers:
                worker.join(timeout=2)
                self.assertFalse(worker.is_alive())
        self.assertEqual(self.events[:2], [("stderr", _FRAME), ("stderr", _CLEAR)])
        self.assertCountEqual(
            self.events[2:], [("stdout", "one\n"), ("stderr", "two\n")],
        )

    def testCleanupPreservesReplacementStreams(self) -> None:
        """
        Verify that cleanup preserves application-replaced streams.

        Returns
        -------
        None
            Assert replacement stdout survives while original stderr is restored.
        """
        replacement = io.StringIO()
        with startup_feedback(["reactor", "list"]):
            sys.stdout = replacement
        self.assertIs(sys.stdout, replacement)
        self.assertIs(sys.stderr, self.stderr)
        self.assertEqual(self.stderr.getvalue(), _FRAME + _CLEAR)

    def testFeedbackIoFailureDoesNotPreventCommandExecution(self) -> None:
        """
        Verify that feedback I/O failure does not prevent command output.

        Returns
        -------
        None
            Assert restored streams and successful output after a display error.
        """
        with (
            patch.object(
                self.stderr, "write", side_effect=OSError("terminal unavailable"),
            ),
            startup_feedback(["reactor", "list"]),
        ):
            self.assertIs(sys.stdout, self.stdout)
            self.assertIs(sys.stderr, self.stderr)
            sys.stdout.write("command\n")
        self.assertEqual(self.stdout.getvalue(), "command\n")

    def testTerminalSizeFallbackRespectsColumns(self) -> None:
        """
        Verify that terminal-size fallback respects the COLUMNS setting.

        Returns
        -------
        None
            Assert a narrow fallback width disables feedback after a query error.
        """
        with (
            patch(
                "orionis.console.startup.os.get_terminal_size", side_effect=OSError,
            ),
            patch.dict(os.environ, {"COLUMNS": "10"}),
            startup_feedback(["reactor", "list"]),
        ):
            self.assertIs(sys.stdout, self.stdout)
        self.assertEqual(self.events, [])

    def testCommandBoundaryProtectsNativeOutputAndRepeatedStops(self) -> None:
        """
        Verify command-boundary cleanup and harmless repeated stops.

        Returns
        -------
        None
            Assert restored streams and one cleanup before direct command output.
        """
        stop_startup_feedback()
        with startup_feedback(["reactor", "native"]):
            stop_startup_feedback()
            stop_startup_feedback()
            self.assertIs(sys.stdout, self.stdout)
            self.assertIs(sys.stderr, self.stderr)
            # A native or subprocess writer uses the original file descriptor.
            self.stdout.write("native output\n")
        stop_startup_feedback()
        self.assertEqual(self.events, [
            ("stderr", _FRAME), ("stderr", _CLEAR),
            ("stdout", "native output\n"),
        ])
