from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exceptions.validation import ValidationException
from orionis.test import TestCase

class TestValidationException(TestCase):

    def testInstantiationStoresFailure(self) -> None:
        """
        Instantiate ValidationException and verify the failure attribute.

        Validates that the exception correctly stores the provided
        ValidationFailure instance on the ``failure`` attribute.
        """
        failure = ValidationFailure(
            field="email",
            rule="pattern",
            message="Invalid email.",
        )
        exc = ValidationException(failure)
        self.assertIs(exc.failure, failure)

    def testMessageIsSetFromFailure(self) -> None:
        """
        Confirm the exception message matches the failure message.

        Validates that the base Exception message is populated from
        the ValidationFailure.message string.
        """
        failure = ValidationFailure(
            field="age",
            rule="gt",
            message="Age must be positive.",
        )
        exc = ValidationException(failure)
        self.assertEqual(str(exc), "Age must be positive.")

    def testErrorReturnsDict(self) -> None:
        """
        Return a Laravel-style payload from the error() method.

        Validates that error() exposes a summary message and the field
        errors indexed by field name.
        """
        failure = ValidationFailure(
            field="name",
            rule="required",
            message="Name is required.",
        )
        exc = ValidationException(failure)
        result = exc.error()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["message"], "Name is required.")
        self.assertEqual(result["errors"], {"name": ["Name is required."]})

    def testErrorDictContainsExactlyTwoKeys(self) -> None:
        """
        Ensure error() dict contains exactly the two expected keys.

        Validates that no extra or missing keys appear in the dictionary
        returned by the error() method.
        """
        failure = ValidationFailure(
            field="score",
            rule="le",
            message="Too high.",
        )
        exc = ValidationException(failure)
        result = exc.error()
        self.assertEqual(set(result.keys()), {"message", "errors"})

    def testMultipleFailuresAreGroupedByField(self) -> None:
        """
        Group every failure message under its own field name.

        Validates that two failures on the same field are reported as a
        list of messages, and that distinct fields get their own entry.
        """
        exc = ValidationException([
            ValidationFailure(field="email", rule="pattern", message="Bad."),
            ValidationFailure(field="email", rule="min_length", message="Short."),
            ValidationFailure(field="age", rule="ge", message="Too young."),
        ])
        self.assertEqual(
            exc.errors,
            {"email": ["Bad.", "Short."], "age": ["Too young."]},
        )

    def testSummaryMessageCountsRemainingErrors(self) -> None:
        """
        Suffix the summary message with the remaining error count.

        Validates that the top-level message mirrors the Laravel format
        when more than one failure is collected.
        """
        exc = ValidationException([
            ValidationFailure(field="a", rule="type", message="First."),
            ValidationFailure(field="b", rule="type", message="Second."),
            ValidationFailure(field="c", rule="type", message="Third."),
        ])
        self.assertEqual(str(exc), "First. (and 2 more errors)")

    def testIsInstanceOfException(self) -> None:
        """
        Confirm ValidationException is a subclass of Exception.

        Validates that it can be caught with a standard except-clause
        targeting the built-in Exception type.
        """
        failure = ValidationFailure(
            field="x",
            rule="required",
            message="Required.",
        )
        exc = ValidationException(failure)
        self.assertIsInstance(exc, Exception)

    def testCanBeRaisedAndCaught(self) -> None:
        """
        Raise and catch ValidationException in a try/except block.

        Validates that the exception propagates and that the failure
        payload survives the raise/catch cycle intact.
        """
        failure = ValidationFailure(
            field="token",
            rule="invalid",
            message="Token is invalid.",
        )
        with self.assertRaises(ValidationException) as ctx:
            raise ValidationException(failure)
        self.assertIs(ctx.exception.failure, failure)
