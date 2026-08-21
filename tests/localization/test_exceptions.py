from orionis.localization.exceptions import (
    InvalidLocaleException,
    TranslationException,
    TranslationFileNotFoundException,
    TranslationSyntaxException,
)
from orionis.test import TestCase

# Every specialized error raised by the localization component.
_SPECIALIZED_EXCEPTIONS: tuple[type[TranslationException], ...] = (
    InvalidLocaleException,
    TranslationFileNotFoundException,
    TranslationSyntaxException,
)

class TestTranslationExceptionHierarchy(TestCase):
    """Validate the inheritance chain of the localization errors."""

    def testBaseExceptionDerivesFromException(self) -> None:
        """
        Derive the localization base error from Exception.

        Validates that the component never raises a BaseException that
        would escape a regular exception handler.
        """
        self.assertTrue(issubclass(TranslationException, Exception))

    def testSpecializedErrorsShareTheSameBase(self) -> None:
        """
        Derive every specialized error from TranslationException.

        Validates that a single except clause is enough to trap any
        localization failure.
        """
        for exception_type in _SPECIALIZED_EXCEPTIONS:
            self.assertTrue(
                issubclass(exception_type, TranslationException),
                exception_type.__name__,
            )

    def testSpecializedErrorsAreDistinctTypes(self) -> None:
        """
        Keep every specialized error a distinct type.

        Validates that callers can discriminate a malformed locale from
        a missing file or an invalid payload.
        """
        self.assertEqual(len(set(_SPECIALIZED_EXCEPTIONS)), 3)

class TestTranslationExceptionBehaviour(TestCase):
    """Validate message preservation and exception chaining."""

    def testMessagePassedToTheConstructorIsPreserved(self) -> None:
        """
        Preserve the message handed to the constructor.

        Validates that the text reported by the framework reaches the
        caller untouched.
        """
        error_msg = "Invalid locale code: '../etc'"
        self.assertEqual(str(InvalidLocaleException(error_msg)), error_msg)

    def testSpecializedErrorIsCaughtByTheBaseClause(self) -> None:
        """
        Trap a specialized error through the base exception.

        Validates the single-catch guarantee offered by the hierarchy.
        """
        error_msg = "Translation file not found: missing.json"
        with self.assertRaises(TranslationException):
            raise TranslationFileNotFoundException(error_msg)

    def testExplicitChainingKeepsTheOriginalCause(self) -> None:
        """
        Keep the original error when re-raising with from.

        Validates that decoding failures preserve the underlying cause
        for debugging.
        """
        origin = ValueError("broken payload")
        error_msg = "Invalid JSON in translation file"
        try:
            raise TranslationSyntaxException(error_msg) from origin
        except TranslationSyntaxException as exc:
            self.assertIs(exc.__cause__, origin)
