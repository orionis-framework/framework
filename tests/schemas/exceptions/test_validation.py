from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exceptions.validation import ValidationException
from orionis.test import TestCase

class TestValidationException(TestCase):

    def testInstantiationStoresFailure(self) -> None:
        """Instantiate ValidationException and verify the failure attribute.

        Validates that the exception correctly stores the provided
        ValidationFailure instance on the ``failure`` attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        failure = ValidationFailure(
            field="email",
            rule="pattern",
            message="Invalid email.",
        )
        exc = ValidationException(failure)
        self.assertIs(exc.failure, failure)

    def testMessageIsSetFromFailure(self) -> None:
        """Confirm the exception message matches the failure message.

        Validates that the base Exception message is populated from
        the ValidationFailure.message string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        Verify that ``error()`` returns the summary and structured field errors.

        Returns
        -------
        None
            Assert the payload's type, summary, rule code, and field message.
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
        self.assertEqual(result["errors"], {
            "name": [{"rule": "required", "message": "Name is required."}],
        })

    def testErrorDictContainsExactlyTwoKeys(self) -> None:
        """Ensure error() dict contains exactly the two expected keys.

        Validates that no extra or missing keys appear in the dictionary
        returned by the error() method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        Verify that every failure code and message is grouped by field.

        Returns
        -------
        None
            Assert grouped details, the summary count, and preserved failures.
        """
        exc = ValidationException([
            ValidationFailure(field="email", rule="pattern", message="Bad."),
            ValidationFailure(field="email", rule="min_length", message="Short."),
            ValidationFailure(field="age", rule="ge", message="Too young."),
        ])
        self.assertEqual(
            exc.errors,
            {
                "email": [
                    {"rule": "pattern", "message": "Bad."},
                    {"rule": "min_length", "message": "Short."},
                ],
                "age": [{"rule": "ge", "message": "Too young."}],
            },
        )
        self.assertEqual(str(exc), "Bad. (and 2 more errors)")
        self.assertEqual(len(exc.failures), 3)
        self.assertIs(exc.failure, exc.failures[0])

    def testSummaryCountsTwoFailuresOnOneField(self) -> None:
        """
        Verify that the summary counts every failure on the same field.

        Returns
        -------
        None
            Assert the remaining-error suffix for two failures on one field.
        """
        exc = ValidationException([
            ValidationFailure(field="name", rule="min_length", message="Short."),
            ValidationFailure(field="name", rule="pattern", message="Bad."),
        ])
        self.assertEqual(str(exc), "Short. (and 1 more error)")

    def testEmptyFailuresUseDefaultMessage(self) -> None:
        """
        Verify the default payload when no failures are supplied.

        Returns
        -------
        None
            Assert the default summary, empty errors, and absent first failure.
        """
        exc = ValidationException([])
        self.assertEqual(exc.error(), {
            "message": "The given data was invalid.", "errors": {},
        })
        self.assertEqual(exc.failures, ())
        self.assertIsNone(exc.failure)

    def testExplicitSummaryPreservesFailureDetails(self) -> None:
        """
        Verify that a custom summary preserves the original failure details.

        Returns
        -------
        None
            Assert the custom summary alongside the field's rule and message.
        """
        failure = ValidationFailure("name", "application_code", "Invalid.")
        exc = ValidationException(failure, message="Check this form.")
        self.assertEqual(exc.error(), {
            "message": "Check this form.",
            "errors": {
                "name": [{"rule": "application_code", "message": "Invalid."}],
            },
        })

    def testSummaryMessageCountsRemainingErrors(self) -> None:
        """Suffix the summary message with the remaining error count.

        Validates that the top-level message mirrors the Laravel format
        when more than one failure is collected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        exc = ValidationException([
            ValidationFailure(field="a", rule="type", message="First."),
            ValidationFailure(field="b", rule="type", message="Second."),
            ValidationFailure(field="c", rule="type", message="Third."),
        ])
        self.assertEqual(str(exc), "First. (and 2 more errors)")

    def testIsInstanceOfException(self) -> None:
        """Confirm ValidationException is a subclass of Exception.

        Validates that it can be caught with a standard except-clause
        targeting the built-in Exception type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        failure = ValidationFailure(
            field="x",
            rule="required",
            message="Required.",
        )
        exc = ValidationException(failure)
        self.assertIsInstance(exc, Exception)

    def testCanBeRaisedAndCaught(self) -> None:
        """Raise and catch ValidationException in a try/except block.

        Validates that the exception propagates and that the failure
        payload survives the raise/catch cycle intact.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        ValidationException
            Raised by this helper to exercise the failure path.
        """
        failure = ValidationFailure(
            field="token",
            rule="invalid",
            message="Token is invalid.",
        )
        with self.assertRaises(ValidationException) as ctx:
            raise ValidationException(failure)
        self.assertIs(ctx.exception.failure, failure)
