from __future__ import annotations
import io
import sys
from unittest.mock import patch
from orionis.console.output.contracts.executor import IExecutor
from orionis.console.output.executor import Executor
from orionis.test import TestCase

class TestExecutor(TestCase):

    # ------------------------------------------------------------------ #
    #  Instantiation & interface                                         #
    # ------------------------------------------------------------------ #

    def testInstantiation(self) -> None:
        """Verify that Executor can be instantiated without arguments.

        Ensures the constructor does not raise any exception and returns
        a valid Executor instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        self.assertIsInstance(executor, Executor)

    def testIsSubclassOfIExecutor(self) -> None:
        """Verify that Executor is a subclass of IExecutor.

        Ensures the concrete implementation satisfies the interface contract
        so it can be used polymorphically wherever IExecutor is expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Executor, IExecutor))

    def testInstanceIsIExecutor(self) -> None:
        """Verify that an Executor instance satisfies isinstance(obj, IExecutor).

        Ensures polymorphic usage is valid and the object passes type checks
        against the abstract interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        self.assertIsInstance(executor, IExecutor)

    # ------------------------------------------------------------------ #
    # Tests for running() method                                         #
    # ------------------------------------------------------------------ #

    def testRunningCallsPrint(self) -> None:
        """Verify that running() produces console output via print.

        Ensures the method delegates to the built-in print function at
        least once for any valid program name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.running("my-program")
            mock_print.assert_called_once()

    def testRunningWithoutTime(self) -> None:
        """Verify that running() works when no time argument is provided.

        Ensures the default empty string for time does not raise any
        exception and still produces output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.running("my-program")
            mock_print.assert_called_once()

    def testRunningWithTime(self) -> None:
        """Verify that running() works when an execution time is provided.

        Ensures the optional time parameter is accepted and the method
        completes without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.running("my-program", time="1.23s")
            mock_print.assert_called_once()

    def testRunningOutputContainsProgramName(self) -> None:
        """Verify that running() output includes the program name.

        Ensures the formatted message written to stdout contains the
        program name string so operators can identify which process runs.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.running("my-service")
        self.assertIn("my-service", buf.getvalue())

    def testRunningOutputContainsRunningLabel(self) -> None:
        """Verify that running() output includes the 'RUNNING' state label.

        Ensures the formatted message contains the state identifier so
        log consumers can parse the execution state.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.running("my-service")
        self.assertIn("RUNNING", buf.getvalue())

    def testRunningWithEmptyProgramName(self) -> None:
        """Verify that running() handles an empty program name without raising.

        Ensures edge-case input (empty string) does not cause the method
        to crash and still produces output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.running("")
            mock_print.assert_called_once()

    # ------------------------------------------------------------------ #
    # Tests for done() method                                            #
    # ------------------------------------------------------------------ #

    def testDoneCallsPrint(self) -> None:
        """Verify that done() produces console output via print.

        Ensures the method delegates to the built-in print function at
        least once for any valid program name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.done("my-program")
            mock_print.assert_called_once()

    def testDoneWithoutTime(self) -> None:
        """Verify that done() works when no time argument is provided.

        Ensures the default empty string for time is accepted and the
        method completes without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.done("my-program")
            mock_print.assert_called_once()

    def testDoneWithTime(self) -> None:
        """Verify that done() works when an execution time is provided.

        Ensures the optional time parameter is forwarded correctly and
        the method completes without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.done("my-program", time="0.42s")
            mock_print.assert_called_once()

    def testDoneOutputContainsProgramName(self) -> None:
        """Verify that done() output includes the program name.

        Ensures the formatted message written to stdout contains the
        program name string for identification purposes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.done("my-service")
        self.assertIn("my-service", buf.getvalue())

    def testDoneOutputContainsDoneLabel(self) -> None:
        """Verify that done() output includes the 'DONE' state label.

        Ensures the formatted message contains the completion state
        identifier so log consumers can parse the execution outcome.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.done("my-service")
        self.assertIn("DONE", buf.getvalue())

    def testDoneOutputContainsTimePrefix(self) -> None:
        """Verify that done() wraps the time argument with ' ~ ' prefix.

        Ensures the implementation prepends the tilde separator to the
        duration string, consistent with the expected output format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.done("svc", time="2.0s")
        self.assertIn("~ 2.0s", buf.getvalue())

    # ------------------------------------------------------------------ #
    # Tests for fail() method                                            #
    # ------------------------------------------------------------------ #

    def testFailCallsPrint(self) -> None:
        """Verify that fail() produces console output via print.

        Ensures the method delegates to the built-in print function at
        least once for any valid program name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.fail("my-program")
            mock_print.assert_called_once()

    def testFailWithoutTime(self) -> None:
        """Verify that fail() works when no time argument is provided.

        Ensures the default empty string for time is accepted and the
        method completes without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.fail("my-program")
            mock_print.assert_called_once()

    def testFailWithTime(self) -> None:
        """Verify that fail() works when an execution time is provided.

        Ensures the optional time parameter is accepted and the method
        completes without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print") as mock_print:
            executor.fail("my-program", time="0.01s")
            mock_print.assert_called_once()

    def testFailOutputContainsProgramName(self) -> None:
        """Verify that fail() output includes the program name.

        Ensures the formatted message written to stdout contains the
        program name string for identification purposes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.fail("broken-svc")
        self.assertIn("broken-svc", buf.getvalue())

    def testFailOutputContainsFailLabel(self) -> None:
        """Verify that fail() output includes the 'FAIL' state label.

        Ensures the formatted message contains the failure state
        identifier so log consumers can detect errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.fail("broken-svc")
        self.assertIn("FAIL", buf.getvalue())

    def testFailOutputContainsTimePrefix(self) -> None:
        """Verify that fail() wraps the time argument with ' ~ ' prefix.

        Ensures the implementation prepends the tilde separator to the
        duration string, consistent with the output format for done().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.fail("svc", time="0.5s")
        self.assertIn("~ 0.5s", buf.getvalue())

    # ------------------------------------------------------------------ #
    #  Output format invariants                                          #
    # ------------------------------------------------------------------ #

    def testRunningOutputContainsTimestamp(self) -> None:
        """Verify that running() output includes a formatted timestamp.

        Ensures the message emitted to stdout contains the date portion
        of the timestamp in YYYY-MM-DD format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.running("svc")
        # A 4-digit year is a reliable proxy for timestamp presence
        self.assertRegex(buf.getvalue(), r"\d{4}-\d{2}-\d{2}")

    def testDoneOutputContainsTimestamp(self) -> None:
        """Verify that done() output includes a formatted timestamp.

        Ensures the message emitted to stdout contains the date portion
        of the timestamp in YYYY-MM-DD format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.done("svc")
        self.assertRegex(buf.getvalue(), r"\d{4}-\d{2}-\d{2}")

    def testFailOutputContainsTimestamp(self) -> None:
        """Verify that fail() output includes a formatted timestamp.

        Ensures the message emitted to stdout contains the date portion
        of the timestamp in YYYY-MM-DD format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            executor.fail("svc")
        self.assertRegex(buf.getvalue(), r"\d{4}-\d{2}-\d{2}")

    def testRunningReturnNone(self) -> None:
        """Verify that running() returns None.

        Ensures the method adheres to the interface contract which
        specifies a None return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print"):
            result = executor.running("svc")
        self.assertIsNone(result)

    def testDoneReturnNone(self) -> None:
        """Verify that done() returns None.

        Ensures the method adheres to the interface contract which
        specifies a None return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print"):
            result = executor.done("svc")
        self.assertIsNone(result)

    def testFailReturnNone(self) -> None:
        """Verify that fail() returns None.

        Ensures the method adheres to the interface contract which
        specifies a None return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        with patch("builtins.print"):
            result = executor.fail("svc")
        self.assertIsNone(result)
