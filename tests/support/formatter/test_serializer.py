# ruff: noqa: PLR2004, PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from unittest.mock import patch
from orionis.support.formatter.exceptions.parser import ExceptionParser
from orionis.support.formatter.serializer import Parser
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Custom exception fixtures
# ---------------------------------------------------------------------------


class _AppError(Exception):
    """Custom exception with a numeric error code."""

    def __init__(self, message: str, code: int) -> None:
        """Initialize the support test double.

        Parameters
        ----------
        message : str
            Value supplied for ``message``.
        code : int
            Value supplied for ``code``.

        Returns
        -------
        None
            No return value.
        """
        super().__init__(message)
        self.code = code


class _NoCodeError(Exception):
    """Custom exception without a code attribute."""


# ---------------------------------------------------------------------------
# Tests for Parser (serializer.py)
# ---------------------------------------------------------------------------


class TestParser(TestCase):
    def testExceptionReturnsExceptionParser(self) -> None:
        """Return an ExceptionParser from the factory method.

        Validates that Parser.exception() produces an instance of
        ExceptionParser when given a valid Exception.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("test")
        result = Parser.exception(exc)
        self.assertIsInstance(result, ExceptionParser)

    def testExceptionAcceptsAnyExceptionType(self) -> None:
        """Accept any Exception subclass as input.

        Validates that Parser.exception() works with different
        built-in exception types without raising errors.

        Returns
        -------
        None
            No return value.
        """
        for exc_cls in (ValueError, RuntimeError, TypeError, KeyError):
            exc = exc_cls("msg")
            result = Parser.exception(exc)
            self.assertIsInstance(result, ExceptionParser)

    def testExceptionResultHasToDictMethod(self) -> None:
        """Expose toDict on the returned ExceptionParser.

        Validates that the object returned by Parser.exception()
        has a callable toDict method.

        Returns
        -------
        None
            No return value.
        """
        exc = Exception("test")
        result = Parser.exception(exc)
        self.assertTrue(callable(result.toDict))


# ---------------------------------------------------------------------------
# Tests for ExceptionParser (exceptions/parser.py)
# ---------------------------------------------------------------------------


class TestExceptionParserToDict(TestCase):
    """Unit tests for ExceptionParser.toDict()."""

    # ------------------------------------------------ return structure

    def testToDictReturnsDict(self) -> None:
        """Return a dict from toDict.

        Validates that toDict produces a plain dict instance
        for any exception.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("something went wrong")
        result = ExceptionParser(exc).toDict()
        self.assertIsInstance(result, dict)

    def testToDictContainsRequiredKeys(self) -> None:
        """Include required keys in toDict output.

        Validates that the dict returned by toDict contains the
        mandatory keys: error_type, error_message, error_code,
        and stack_trace.

        Returns
        -------
        None
            No return value.
        """
        exc = RuntimeError("fail")
        result = ExceptionParser(exc).toDict()
        self.assertIn("error_type", result)
        self.assertIn("error_message", result)
        self.assertIn("error_code", result)
        self.assertIn("stack_trace", result)

    # ------------------------------------------------ error_type

    def testToDictErrorTypeMatchesExceptionClass(self) -> None:
        """Report the correct exception class name as error_type.

        Validates that error_type reflects the actual class name
        of the provided exception.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("bad value")
        result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "ValueError")

    def testToDictErrorTypeForRuntimeError(self) -> None:
        """Report RuntimeError as error_type for RuntimeError exceptions.

        Validates that the error_type field correctly identifies
        RuntimeError exceptions.

        Returns
        -------
        None
            No return value.
        """
        exc = RuntimeError("oops")
        result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "RuntimeError")

    def testToDictErrorTypeForCustomException(self) -> None:
        """Report custom exception class name as error_type.

        Validates that error_type reflects the name of a user-defined
        exception class.

        Returns
        -------
        None
            No return value.
        """
        exc = _AppError("custom", code=500)
        result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "_AppError")

    def testToDictErrorTypeIsString(self) -> None:
        """Return error_type as a str instance.

        Validates that error_type is always a string, never None
        or another type.

        Returns
        -------
        None
            No return value.
        """
        exc = Exception("generic")
        result = ExceptionParser(exc).toDict()
        self.assertIsInstance(result["error_type"], str)

    # ------------------------------------------------ error_message

    def testToDictErrorMessageIsString(self) -> None:
        """Return error_message as a str instance.

        Validates that error_message is always a string in the
        toDict output.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("test message")
        result = ExceptionParser(exc).toDict()
        self.assertIsInstance(result["error_message"], str)

    def testToDictErrorMessageIsNotEmpty(self) -> None:
        """Return non-empty error_message for a raised exception.

        Validates that the error_message field is not empty when
        the exception has a meaningful message.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("non-empty message")
        result = ExceptionParser(exc).toDict()
        self.assertTrue(len(result["error_message"]) > 0)

    # ------------------------------------------------ error_code

    def testToDictErrorCodeIsNoneWhenNotPresent(self) -> None:
        """Return None for error_code when the attribute is absent.

        Validates that error_code is None for exceptions that do
        not define a code attribute.

        Returns
        -------
        None
            No return value.
        """
        exc = _NoCodeError("no code here")
        result = ExceptionParser(exc).toDict()
        self.assertIsNone(result["error_code"])

    def testToDictErrorCodeReflectsCustomCode(self) -> None:
        """Return the custom error code from the exception.

        Validates that error_code matches the code attribute set
        on a custom exception class.

        Returns
        -------
        None
            No return value.
        """
        exc = _AppError("custom error", code=404)
        result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_code"], 404)

    def testToDictErrorCodeForBuiltinExceptions(self) -> None:
        """Return None for error_code on standard exceptions.

        Validates that built-in exceptions without a code attribute
        produce None under error_code.

        Returns
        -------
        None
            No return value.
        """
        for exc_cls in (ValueError, TypeError, RuntimeError):
            exc = exc_cls("msg")
            result = ExceptionParser(exc).toDict()
            self.assertIsNone(result["error_code"])

    # ------------------------------------------------ stack_trace

    def testToDictStackTraceIsList(self) -> None:
        """Return stack_trace as a list.

        Validates that the stack_trace field in toDict output is
        always a list instance.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("trace test")
        result = ExceptionParser(exc).toDict()
        self.assertIsInstance(result["stack_trace"], list)

    def testToDictStackTraceContainsDictsWhenRaised(self) -> None:
        """Populate stack_trace with dicts for a raised exception.

        Validates that each entry in stack_trace is a dict when
        the exception was actually raised in a call stack.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "raised error"
            raise ValueError(error_msg)
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            self.assertIsInstance(frame, dict)

    def testToDictStackTraceFrameHasRequiredKeys(self) -> None:
        """Include required keys in each stack frame dict.

        Validates that stack_trace frames contain the keys:
        id, filename, lineno, name, line_code, code, lines,
        and code_with_lines.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        RuntimeError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "frame test"
            raise RuntimeError(error_msg)
        except RuntimeError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            self.assertIn("id", frame)
            self.assertIn("filename", frame)
            self.assertIn("lineno", frame)
            self.assertIn("name", frame)
            self.assertIn("line_code", frame)
            self.assertIn("code", frame)
            self.assertIn("lines", frame)
            self.assertIn("code_with_lines", frame)

    def testToDictStackTraceFrameIdIsInt(self) -> None:
        """Return integer ids in stack frame entries.

        Validates that the 'id' field in each stack frame is an
        integer identifying the frame position.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        TypeError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "id test"
            raise TypeError(error_msg)
        except TypeError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            self.assertIsInstance(frame["id"], int)

    def testToDictStackTraceFrameIdsIncreaseFromMostRecent(self) -> None:
        """Assign frame identifiers in most-recent-first order.

        Returns
        -------
        None
            No return value.
        """
        try:

            def inner() -> None:
                """Raise an inner error for stack-frame inspection.

                Returns
                -------
                None
                    No return value.

                Raises
                ------
                ValueError
                    Raised by this helper to exercise the failure path.
                """
                error_message = "frame ids"
                raise ValueError(error_message)

            inner()
        except ValueError as exc:
            frames = ExceptionParser(exc).toDict()["stack_trace"]

        self.assertEqual(len(frames), 2)
        self.assertEqual(
            [frame["id"] for frame in frames],
            list(range(1, len(frames) + 1)),
        )

    def testToDictStackTraceFilenameUsesForwardSlashes(self) -> None:
        """Use forward slashes in frame filenames.

        Validates that backslashes in file paths are normalized
        to forward slashes in stack frame filenames.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "slash test"
            raise ValueError(error_msg)
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            self.assertNotIn("\\", frame["filename"])

    def testToDictStackTraceCodeIsList(self) -> None:
        """Return 'code' as a list in each stack frame.

        Validates that the 'code' field in each stack frame is
        a list of source code strings.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "code list test"
            raise ValueError(error_msg)
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            self.assertIsInstance(frame["code"], list)

    def testToDictStackTraceLinesIsListOfInts(self) -> None:
        """Return 'lines' as a list of ints in each stack frame.

        Validates that line numbers in stack frames are stored as
        a list of integers.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "lines test"
            raise ValueError(error_msg)
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            for ln in frame["lines"]:
                self.assertIsInstance(ln, int)

    def testToDictStackTraceCodeWithLinesContainsColon(self) -> None:
        """Format code_with_lines entries as 'lineno:code'.

        Validates that each entry in code_with_lines uses the
        expected 'line:code' format with a colon separator.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "code_with_lines test"
            raise ValueError(error_msg)
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            for entry in frame["code_with_lines"]:
                self.assertIn(":", entry)

    def testToDictStackTraceIsMostRecentFirst(self) -> None:
        """Order stack frames with the most recent frame first.

        Validates that stack_trace is reversed so the innermost
        (most recent) frame appears at index 0.

        Returns
        -------
        None
            No return value.
        """
        try:

            def inner() -> None:
                """Raise an inner error for stack-frame inspection.

                Returns
                -------
                None
                    No return value.

                Raises
                ------
                ValueError
                    Raised by this helper to exercise the failure path.
                """
                error_msg = "inner error"
                raise ValueError(error_msg)

            inner()
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        frames = result["stack_trace"]
        if len(frames) >= 2:
            # Check that the innermost function appears first.
            first_name = frames[0]["name"]
            self.assertEqual(first_name, "inner")

    # ------------------------------------------------ edge cases

    def testToDictWithBaseException(self) -> None:
        """Handle base Exception class correctly.

        Validates that toDict works without error for the most
        generic Exception type.

        Returns
        -------
        None
            No return value.
        """
        exc = Exception("base")
        result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "Exception")
        self.assertIsInstance(result["stack_trace"], list)

    def testToDictWithKeyError(self) -> None:
        """Handle KeyError serialization correctly.

        Validates that KeyError (whose str includes quotes) is
        parsed and produces valid toDict output.

        Returns
        -------
        None
            No return value.
        """
        try:
            d: dict = {}
            _ = d["missing"]
        except KeyError as exc:
            result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "KeyError")

    def testToDictWithZeroDivisionError(self) -> None:
        """Handle ZeroDivisionError serialization.

        Validates that a ZeroDivisionError raised in code is parsed
        and produces a non-empty stack_trace.

        Returns
        -------
        None
            No return value.
        """
        try:
            _ = 1 / 0
        except ZeroDivisionError as exc:
            result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "ZeroDivisionError")
        self.assertGreater(len(result["stack_trace"]), 0)

    def testToDictWithExceptionConstructedDirectly(self) -> None:
        """Parse exceptions constructed without raising.

        Validates that an exception instantiated but not raised
        still produces valid toDict output with an empty stack.

        Returns
        -------
        None
            No return value.
        """
        exc = ValueError("not raised")
        result = ExceptionParser(exc).toDict()
        self.assertEqual(result["error_type"], "ValueError")
        self.assertIsInstance(result["stack_trace"], list)


class TestExceptionParserGetSourceCode(TestCase):
    def testSourceContextIncludesTwoLinesBeforeAndAfter(self) -> None:
        """Return the requested line and two neighboring lines per side.

        Returns
        -------
        None
            No return value.
        """
        parser = ExceptionParser.__new__(ExceptionParser)
        source = [f"line {number}\n" for number in range(1, 11)]
        with patch(
            "orionis.support.formatter.exceptions.parser.getlines",
            return_value=source,
        ):
            lines, code = parser._getSourceCode("sample.py", 5)

        self.assertEqual(lines, [3, 4, 5, 6, 7])
        self.assertEqual(code, [f"line {number}" for number in lines])

    def testSourceContextClipsAtFileBoundaries(self) -> None:
        """Limit source context to lines present in the file.

        Returns
        -------
        None
            No return value.
        """
        parser = ExceptionParser.__new__(ExceptionParser)
        source = [f"line {number}\n" for number in range(1, 11)]
        with patch(
            "orionis.support.formatter.exceptions.parser.getlines",
            return_value=source,
        ):
            lines, code = parser._getSourceCode("sample.py", 1)

        self.assertEqual(lines, [1, 2, 3])
        self.assertEqual(code, ["line 1", "line 2", "line 3"])

    def testSourceCodeLinesAreIncludedInFrames(self) -> None:
        """Include surrounding source lines in stack frames.

        Validates that a raised exception with a known source file
        includes source code lines in the frame's 'code' list.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        RuntimeError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "source test"
            raise RuntimeError(error_msg)
        except RuntimeError as exc:
            result = ExceptionParser(exc).toDict()

        # At least one frame should have code lines extracted
        has_code = any(len(f["code"]) > 0 for f in result["stack_trace"])
        self.assertTrue(has_code)

    def testLineNumbersArePositiveIntegers(self) -> None:
        """Return positive integers for all line numbers in frames.

        Validates that every line number reported in stack frames
        is a positive integer.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        try:
            error_msg = "lineno test"
            raise ValueError(error_msg)
        except ValueError as exc:
            result = ExceptionParser(exc).toDict()

        self.assertTrue(result["stack_trace"])
        for frame in result["stack_trace"]:
            self.assertIsInstance(frame["lineno"], int)
            self.assertGreater(frame["lineno"], 0)
