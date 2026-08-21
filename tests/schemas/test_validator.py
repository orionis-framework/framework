from typing import Annotated
import msgspec
from orionis.schemas.constraints import (
    Email,
    GreaterThan,
    GreaterThanOrEqual,
    LessThan,
    LessThanOrEqual,
    MaxLength,
    MinLength,
    MultipleOf,
    Pattern,
    StrongPassword,
)
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.metadata import Message
from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

class _PersonSchema(Schema):
    name: str
    age: int

class _WithDefaultsSchema(Schema):
    label: str = "default"
    count: int = 0

class _ConstrainedSchema(Schema):
    score: Annotated[int, GreaterThanOrEqual(0), LessThanOrEqual(100)]
    tag: Annotated[str, MinLength(2), MaxLength(20)]

class _PatternSchema(Schema):
    code: Annotated[str, Pattern(r"^\d{4}$")]

class _MultipleOfSchema(Schema):
    quantity: Annotated[int, MultipleOf(5)]

class _NullableSchema(Schema):
    value: int | None

class _PasswordSchema(Schema):
    password: Annotated[str, StrongPassword()]

class _MessageSchema(Schema):
    name: Annotated[str, Message("Name must be a string.")]

class _NestedAddress(Schema):
    zip_code: str

class _NestedPersonSchema(Schema):
    address: _NestedAddress
    age: int

class _CredentialsSchema(Schema):
    email: Annotated[str, MinLength(5), Email()]
    password: Annotated[str, MinLength(8)]

class _PlainStruct(msgspec.Struct):
    label: str

class TestValidatorBasic(TestCase):

    def testValidPayloadReturnsInstance(self) -> None:
        """
        Return a schema instance for a valid payload.

        Validates that Validator.validate converts a valid dict to the
        expected schema class instance.
        """
        result = Validator.validate({"name": "Alice", "age": 30}, _PersonSchema)
        self.assertIsInstance(result, _PersonSchema)

    def testValidPayloadFieldValues(self) -> None:
        """
        Return correct field values for a valid payload.

        Validates that the converted schema instance carries the same
        field values as the original input dict.
        """
        result = Validator.validate({"name": "Bob", "age": 25}, _PersonSchema)
        self.assertEqual(result.name, "Bob")
        self.assertEqual(result.age, 25)

    def testInvalidTypeRaisesValidationException(self) -> None:
        """
        Raise ValidationException when a field has the wrong type.

        Validates that a type mismatch in the payload causes the validator
        to raise a ValidationException.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"name": "Alice", "age": "not_int"}, _PersonSchema)

    def testMissingRequiredFieldRaisesValidationException(self) -> None:
        """
        Raise ValidationException when a required field is absent.

        Validates that an incomplete payload raises a ValidationException.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"name": "Alice"}, _PersonSchema)

    def testDefaultValuesAreApplied(self) -> None:
        """
        Apply default values when optional fields are missing from payload.

        Validates that a schema with defaults is correctly instantiated
        using the fallback values.
        """
        result = Validator.validate({}, _WithDefaultsSchema)
        self.assertEqual(result.label, "default")
        self.assertEqual(result.count, 0)

class TestValidatorConstraints(TestCase):

    def testScoreWithinBoundsIsAccepted(self) -> None:
        """
        Accept a score value within the declared inclusive bounds.

        Validates that GreaterThanOrEqual(0) and LessThanOrEqual(100)
        are satisfied by values inside the range.
        """
        result = Validator.validate({"score": 50, "tag": "ok"}, _ConstrainedSchema)
        self.assertEqual(result.score, 50)

    def testScoreTooLowRaisesValidationException(self) -> None:
        """
        Raise ValidationException when score is below the lower bound.

        Validates that GreaterThanOrEqual(0) rejects negative scores.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"score": -1, "tag": "ok"}, _ConstrainedSchema)

    def testScoreTooHighRaisesValidationException(self) -> None:
        """
        Raise ValidationException when score exceeds the upper bound.

        Validates that LessThanOrEqual(100) rejects scores above 100.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"score": 101, "tag": "ok"}, _ConstrainedSchema)

    def testTagTooShortRaisesValidationException(self) -> None:
        """
        Raise ValidationException when tag length is below the minimum.

        Validates that MinLength(2) rejects single-character strings.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"score": 50, "tag": "x"}, _ConstrainedSchema)

    def testTagTooLongRaisesValidationException(self) -> None:
        """
        Raise ValidationException when tag length exceeds the maximum.

        Validates that MaxLength(20) rejects strings longer than 20 chars.
        """
        with self.assertRaises(ValidationException):
            Validator.validate(
                {"score": 50, "tag": "x" * 21}, _ConstrainedSchema,
            )

    def testPatternMatchingIsAccepted(self) -> None:
        """
        Accept a value matching the Pattern constraint regex.

        Validates that a four-digit string passes the Pattern constraint
        for exactly four digits.
        """
        result = Validator.validate({"code": "1234"}, _PatternSchema)
        self.assertEqual(result.code, "1234")

    def testPatternMismatchRaisesValidationException(self) -> None:
        """
        Raise ValidationException when value does not match the Pattern.

        Validates that a non-matching string triggers a ValidationException.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"code": "abcd"}, _PatternSchema)

    def testMultipleOfIsAccepted(self) -> None:
        """
        Accept a value that is a multiple of the declared divisor.

        Validates that MultipleOf(5) accepts 15.
        """
        result = Validator.validate({"quantity": 15}, _MultipleOfSchema)
        self.assertEqual(result.quantity, 15)

    def testMultipleOfViolationRaisesValidationException(self) -> None:
        """
        Raise ValidationException when value is not a multiple of the divisor.

        Validates that MultipleOf(5) rejects 7.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"quantity": 7}, _MultipleOfSchema)

class TestValidatorCustomRules(TestCase):

    def testStrongPasswordIsAccepted(self) -> None:
        """
        Accept a strong password that satisfies all StrongPassword rules.

        Validates that a password with uppercase, lowercase, digit, and
        sufficient length passes the custom rule validation.
        """
        result = Validator.validate({"password": "Secure1!"}, _PasswordSchema)
        self.assertEqual(result.password, "Secure1!")

    def testWeakPasswordRaisesValidationException(self) -> None:
        """
        Raise ValidationException for a password that fails StrongPassword.

        Validates that a weak password triggers the custom rule and causes
        a ValidationException to be raised.
        """
        with self.assertRaises(ValidationException):
            Validator.validate({"password": "weakpass"}, _PasswordSchema)

    def testValidationExceptionContainsFailure(self) -> None:
        """
        Confirm ValidationException.failure is populated on rule failure.

        Validates that the raised exception carries a non-None failure
        attribute with the correct rule code.
        """
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate({"password": "weakpass"}, _PasswordSchema)
        self.assertEqual(ctx.exception.failure.rule, "strong_password")

class TestValidatorNullable(TestCase):

    def testNullableFieldAcceptsNone(self) -> None:
        """
        Accept None for a field annotated as Nullable.

        Validates that a payload with value=None is converted without
        raising a ValidationException.
        """
        result = Validator.validate({"value": None}, _NullableSchema)
        self.assertIsNone(result.value)

    def testNullableFieldAcceptsInt(self) -> None:
        """
        Accept an integer for a Nullable[int] field.

        Validates that a payload with a valid integer is accepted
        alongside the None possibility.
        """
        result = Validator.validate({"value": 42}, _NullableSchema)
        self.assertEqual(result.value, 42)

class TestValidatorCustomMessage(TestCase):

    def testCustomTypeMessageAppearsInException(self) -> None:
        """
        Surface a custom Message text in the ValidationException on type error.

        Validates that when a field annotated with Message(...) receives the
        wrong type the exception message matches the custom text.
        """
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate({"name": 123}, _MessageSchema)
        self.assertIn("Name must be a string.", ctx.exception.failure.message)

class TestValidatorNestedSchema(TestCase):

    def testValidNestedPayloadIsAccepted(self) -> None:
        """
        Accept a valid nested schema payload.

        Validates that nested schemas are converted correctly when all
        required fields are present.
        """
        payload = {"address": {"zip_code": "10001"}, "age": 30}
        result = Validator.validate(payload, _NestedPersonSchema)
        self.assertIsInstance(result, _NestedPersonSchema)
        self.assertEqual(result.address.zip_code, "10001")

    def testInvalidNestedFieldRaisesValidationException(self) -> None:
        """
        Raise ValidationException when a nested field has the wrong type.

        Validates that type errors in nested schema fields propagate as
        ValidationException correctly.
        """
        payload = {"address": {"zip_code": 12345}, "age": 30}
        with self.assertRaises(ValidationException):
            Validator.validate(payload, _NestedPersonSchema)

    def testValidatorErrorMethodReturnsDict(self) -> None:
        """
        Return a dict from ValidationException.error() for nested errors.

        Validates that the error() method surfaces a summary message and
        the dotted field path of failures in nested schema fields.
        """
        payload = {"address": {"zip_code": 99}, "age": 1}
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate(payload, _NestedPersonSchema)
        err = ctx.exception.error()
        self.assertIn("message", err)
        self.assertIn("errors", err)
        self.assertIn("address.zip_code", err["errors"])

class TestValidatorMultipleErrors(TestCase):

    def testEveryInvalidFieldIsReported(self) -> None:
        """
        Report every invalid field instead of stopping at the first one.

        Validates that a payload breaking two constraints produces one
        entry per offending field.
        """
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate({"score": 500, "tag": "x"}, _ConstrainedSchema)
        self.assertEqual(
            set(ctx.exception.errors.keys()),
            {"score", "tag"},
        )

    def testMissingFieldsAreAllReported(self) -> None:
        """
        Report every missing required field at once.

        Validates that an empty payload lists all required fields rather
        than only the first one detected by msgspec.
        """
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate({}, _PersonSchema)
        self.assertEqual(set(ctx.exception.errors.keys()), {"name", "age"})

    def testNestedAndRootErrorsAreCombined(self) -> None:
        """
        Combine nested schema errors with root-level errors.

        Validates that failures inside a nested schema are reported with a
        dotted path alongside failures of the parent schema.
        """
        payload = {"address": {"zip_code": 99}, "age": "old"}
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate(payload, _NestedPersonSchema)
        self.assertEqual(
            set(ctx.exception.errors.keys()),
            {"address.zip_code", "age"},
        )

    def testMessagesAreListsOfStrings(self) -> None:
        """
        Expose every field error as a list of message strings.

        Validates the response contract consumed by the HTTP layer, where
        each field maps to an array of messages.
        """
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate({"name": 1, "age": "x"}, _PersonSchema)
        for messages in ctx.exception.errors.values():
            self.assertIsInstance(messages, list)
            for message in messages:
                self.assertIsInstance(message, str)

    def testCustomRulesRunWhenAnotherFieldFailsConversion(self) -> None:
        """
        Run custom rules even when a sibling field breaks a constraint.

        Validates that a rule such as ``Email`` still reports its failure
        when msgspec aborts the whole-payload conversion because of another
        field.
        """
        payload = {"email": "not-an-email", "password": "123"}
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate(payload, _CredentialsSchema)
        self.assertEqual(
            set(ctx.exception.errors.keys()),
            {"email", "password"},
        )

    def testCustomRuleIsSkippedWhenItsOwnFieldIsInvalid(self) -> None:
        """
        Skip a custom rule when its own field failed conversion.

        Validates that only the constraint failure is reported, since the
        rule has no converted value to inspect.
        """
        payload = {"email": "a@b", "password": "12345678"}
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate(payload, _CredentialsSchema)
        messages = ctx.exception.errors["email"]
        self.assertEqual(len(messages), 1)
        self.assertNotIn("email address", messages[0])

class TestValidatorGreaterThan(TestCase):

    def testGreaterThanIsEnforced(self) -> None:
        """
        Raise ValidationException when a GreaterThan constraint is violated.

        Validates that a value equal to the lower bound is rejected by
        the exclusive GreaterThan constraint.
        """

        class _GtSchema(Schema):
            n: Annotated[int, GreaterThan(0)]

        with self.assertRaises(ValidationException):
            Validator.validate({"n": 0}, _GtSchema)

    def testGreaterThanAcceptsValueAboveBound(self) -> None:
        """
        Accept a value strictly above the GreaterThan lower bound.

        Validates that a value of 1 satisfies GreaterThan(0).
        """

        class _GtSchema(Schema):
            n: Annotated[int, GreaterThan(0)]

        result = Validator.validate({"n": 1}, _GtSchema)
        self.assertEqual(result.n, 1)

    def testLessThanIsEnforced(self) -> None:
        """
        Raise ValidationException when a LessThan constraint is violated.

        Validates that a value equal to the upper bound is rejected by
        the exclusive LessThan constraint.
        """

        class _LtSchema(Schema):
            n: Annotated[int, LessThan(10)]

        with self.assertRaises(ValidationException):
            Validator.validate({"n": 10}, _LtSchema)

class TestValidatorWithPlainStruct(TestCase):

    def testPlanIsBuiltForAStructWithoutAPrebuiltPlan(self) -> None:
        """
        Validate a struct that the schema metaclass never processed.

        Validates that the validation plan is built on demand instead of
        assuming the class was prepared at definition time.
        """
        result = Validator.validate({"label": "raw"}, _PlainStruct)
        self.assertIsInstance(result, _PlainStruct)
        self.assertEqual(result.label, "raw")

    def testNonMappingPayloadRaisesValidationException(self) -> None:
        """
        Raise ValidationException when the payload is not a mapping.

        Validates that the original conversion error is still reported
        when no declared field can be blamed for it.
        """
        with self.assertRaises(ValidationException) as ctx:
            Validator.validate([1, 2], _PersonSchema)
        self.assertEqual(len(ctx.exception.failures), 1)
