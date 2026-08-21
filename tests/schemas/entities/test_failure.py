from orionis.schemas.entities.failure import ValidationFailure
from orionis.test import TestCase

class TestValidationFailure(TestCase):

    def testInstantiationStoresFields(self) -> None:
        """
        Instantiate ValidationFailure and verify stored attributes.

        Validates that the constructor correctly persists all three
        required fields as immutable attributes.
        """
        failure = ValidationFailure(
            field="username",
            rule="required",
            message="This field is required.",
        )
        self.assertEqual(failure.field, "username")
        self.assertEqual(failure.rule, "required")
        self.assertEqual(failure.message, "This field is required.")

    def testToDictReturnsCorrectMapping(self) -> None:
        """
        Convert a ValidationFailure to a dictionary.

        Validates that toDict returns a plain dict with the expected
        keys and values matching the instance attributes.
        """
        failure = ValidationFailure(
            field="email",
            rule="pattern",
            message="Invalid email format.",
        )
        result = failure.toDict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["field"], "email")
        self.assertEqual(result["rule"], "pattern")
        self.assertEqual(result["message"], "Invalid email format.")

    def testToDictContainsExactlyThreeKeys(self) -> None:
        """
        Ensure toDict output contains exactly the three expected keys.

        Validates that no extra or missing keys appear in the returned
        dictionary.
        """
        failure = ValidationFailure(
            field="age",
            rule="gt",
            message="Must be greater than zero.",
        )
        result = failure.toDict()
        self.assertEqual(set(result.keys()), {"field", "rule", "message"})

    def testImmutabilityPreventsFieldMutation(self) -> None:
        """
        Confirm that ValidationFailure is immutable (frozen dataclass).

        Validates that attempting to modify an attribute raises an
        AttributeError or FrozenInstanceError.
        """
        failure = ValidationFailure(
            field="name",
            rule="min_length",
            message="Too short.",
        )
        with self.assertRaises(AttributeError):
            failure.field = "other"  # type: ignore[misc]

    def testEmptyStringFieldsAreAccepted(self) -> None:
        """
        Accept empty strings for all three fields of ValidationFailure.

        Validates that no error is raised when empty strings are supplied
        and that the values are preserved faithfully.
        """
        failure = ValidationFailure(field="", rule="", message="")
        self.assertEqual(failure.field, "")
        self.assertEqual(failure.rule, "")
        self.assertEqual(failure.message, "")

    def testToDictValuesMatchInstanceAttributes(self) -> None:
        """
        Verify that toDict values are identical to instance attributes.

        Validates that the dictionary is not a deep copy but reflects
        the same string objects for each field.
        """
        failure = ValidationFailure(
            field="score",
            rule="le",
            message="Score too high.",
        )
        result = failure.toDict()
        self.assertIs(result["field"], failure.field)
        self.assertIs(result["rule"], failure.rule)
        self.assertIs(result["message"], failure.message)
