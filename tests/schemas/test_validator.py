import asyncio
from inspect import iscoroutinefunction
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
from orionis.schemas.rule import Rule
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

class _RejectAsyncRule(Rule):
    """Reject only after yielding to the current event loop."""

    __code__ = "reject_async"
    __message__ = "Rejected asynchronously."

    async def enforceAsync(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        """Reject the converted value without using synchronous enforcement."""
        await asyncio.sleep(0)
        return False

class _MixedRulesSchema(Schema):
    password: Annotated[str, StrongPassword(), _RejectAsyncRule()]
    count: int

class TestValidatorBasic(TestCase):

    def testValidateIsAlwaysAsync(self) -> None:
        """Expose validation as a coroutine even for schemas without rules."""
        self.assertTrue(iscoroutinefunction(Validator.validate))

    def testValidatorHasNoAlternateEntryPoint(self) -> None:
        """Expose only one validation entry point."""
        self.assertFalse(hasattr(Validator, "validateAsync"))

    async def testValidPayloadReturnsInstance(self) -> None:
        """Return a schema instance for a valid payload.

        Validates that Validator.validate converts a valid dict to the
        expected schema class instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"name": "Alice", "age": 30}, _PersonSchema)
        self.assertIsInstance(result, _PersonSchema)

    async def testValidPayloadFieldValues(self) -> None:
        """Return correct field values for a valid payload.

        Validates that the converted schema instance carries the same
        field values as the original input dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"name": "Bob", "age": 25}, _PersonSchema)
        self.assertEqual(result.name, "Bob")
        self.assertEqual(result.age, 25)

    async def testInvalidTypeRaisesValidationException(self) -> None:
        """Raise ValidationException when a field has the wrong type.

        Validates that a type mismatch in the payload causes the validator
        to raise a ValidationException.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"name": "Alice", "age": "not_int"}, _PersonSchema)

    async def testMissingRequiredFieldRaisesValidationException(self) -> None:
        """Raise ValidationException when a required field is absent.

        Validates that an incomplete payload raises a ValidationException.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"name": "Alice"}, _PersonSchema)

    async def testDefaultValuesAreApplied(self) -> None:
        """Apply default values when optional fields are missing from payload.

        Validates that a schema with defaults is correctly instantiated
        using the fallback values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({}, _WithDefaultsSchema)
        self.assertEqual(result.label, "default")
        self.assertEqual(result.count, 0)

class TestValidatorConstraints(TestCase):

    async def testScoreWithinBoundsIsAccepted(self) -> None:
        """Accept a score value within the declared inclusive bounds.

        Validates that GreaterThanOrEqual(0) and LessThanOrEqual(100)
        are satisfied by values inside the range.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate(
            {"score": 50, "tag": "ok"}, _ConstrainedSchema,
        )
        self.assertEqual(result.score, 50)

    async def testScoreTooLowRaisesValidationException(self) -> None:
        """Raise ValidationException when score is below the lower bound.

        Validates that GreaterThanOrEqual(0) rejects negative scores.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"score": -1, "tag": "ok"}, _ConstrainedSchema)

    async def testScoreTooHighRaisesValidationException(self) -> None:
        """Raise ValidationException when score exceeds the upper bound.

        Validates that LessThanOrEqual(100) rejects scores above 100.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"score": 101, "tag": "ok"}, _ConstrainedSchema)

    async def testTagTooShortRaisesValidationException(self) -> None:
        """Raise ValidationException when tag length is below the minimum.

        Validates that MinLength(2) rejects single-character strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"score": 50, "tag": "x"}, _ConstrainedSchema)

    async def testTagTooLongRaisesValidationException(self) -> None:
        """Raise ValidationException when tag length exceeds the maximum.

        Validates that MaxLength(20) rejects strings longer than 20 chars.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate(
                {"score": 50, "tag": "x" * 21}, _ConstrainedSchema,
            )

    async def testPatternMatchingIsAccepted(self) -> None:
        """Accept a value matching the Pattern constraint regex.

        Validates that a four-digit string passes the Pattern constraint
        for exactly four digits.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"code": "1234"}, _PatternSchema)
        self.assertEqual(result.code, "1234")

    async def testPatternMismatchRaisesValidationException(self) -> None:
        """Raise ValidationException when value does not match the Pattern.

        Validates that a non-matching string triggers a ValidationException.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"code": "abcd"}, _PatternSchema)

    async def testMultipleOfIsAccepted(self) -> None:
        """Accept a value that is a multiple of the declared divisor.

        Validates that MultipleOf(5) accepts 15.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"quantity": 15}, _MultipleOfSchema)
        self.assertEqual(result.quantity, 15)

    async def testMultipleOfViolationRaisesValidationException(self) -> None:
        """Raise ValidationException when value is not a multiple of the divisor.

        Validates that MultipleOf(5) rejects 7.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"quantity": 7}, _MultipleOfSchema)

class TestValidatorCustomRules(TestCase):

    async def testMixedRulesKeepTheirOrderOnBothConversionPaths(self) -> None:
        """Collect sync and native async failures even after a sibling type error."""
        for count in (1, "invalid"):
            with (
                self.subTest(count=count),
                self.assertRaises(ValidationException) as caught,
            ):
                await Validator.validate(
                    {"password": "weakpass", "count": count}, _MixedRulesSchema,
                )
            failures = [
                (failure.field, failure.rule)
                for failure in caught.exception.failures
                if failure.field == "password"
            ]
            self.assertEqual(failures, [
                ("password", "strong_password"),
                ("password", "reject_async"),
            ])
            self.assertEqual(
                set(caught.exception.errors),
                {"password"} if count == 1 else {"password", "count"},
            )
            if count != 1:
                self.assertIsInstance(
                    caught.exception.__cause__, msgspec.ValidationError,
                )

    async def testAsyncRulesSkipTheirOwnUnconvertedField(self) -> None:
        """Report a type error without invoking rules on an invalid field value."""
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(
                {"password": 123, "count": 1}, _MixedRulesSchema,
            )
        self.assertEqual(len(caught.exception.failures), 1)
        self.assertEqual(caught.exception.failure.field, "password")
        self.assertNotIn(
            caught.exception.failure.rule, ("strong_password", "reject_async"),
        )

    async def testStrongPasswordIsAccepted(self) -> None:
        """Accept a strong password that satisfies all StrongPassword rules.

        Validates that a password with uppercase, lowercase, digit, and
        sufficient length passes the custom rule validation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"password": "Secure1!"}, _PasswordSchema)
        self.assertEqual(result.password, "Secure1!")

    async def testWeakPasswordRaisesValidationException(self) -> None:
        """Raise ValidationException for a password that fails StrongPassword.

        Validates that a weak password triggers the custom rule and causes
        a ValidationException to be raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException):
            await Validator.validate({"password": "weakpass"}, _PasswordSchema)

    async def testValidationExceptionContainsFailure(self) -> None:
        """Confirm ValidationException.failure is populated on rule failure.

        Validates that the raised exception carries a non-None failure
        attribute with the correct rule code.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate({"password": "weakpass"}, _PasswordSchema)
        self.assertEqual(ctx.exception.failure.rule, "strong_password")

class TestValidatorNullable(TestCase):

    async def testNullableFieldAcceptsNone(self) -> None:
        """Accept None for a field annotated as Nullable.

        Validates that a payload with value=None is converted without
        raising a ValidationException.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"value": None}, _NullableSchema)
        self.assertIsNone(result.value)

    async def testNullableFieldAcceptsInt(self) -> None:
        """Accept an integer for a Nullable[int] field.

        Validates that a payload with a valid integer is accepted
        alongside the None possibility.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"value": 42}, _NullableSchema)
        self.assertEqual(result.value, 42)

class TestValidatorCustomMessage(TestCase):

    async def testCustomTypeMessageAppearsInException(self) -> None:
        """Surface a custom Message text in the ValidationException on type error.

        Validates that when a field annotated with Message(...) receives the
        wrong type the exception message matches the custom text.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate({"name": 123}, _MessageSchema)
        self.assertIn("Name must be a string.", ctx.exception.failure.message)

class TestValidatorNestedSchema(TestCase):

    async def testValidNestedPayloadIsAccepted(self) -> None:
        """Accept a valid nested schema payload.

        Validates that nested schemas are converted correctly when all
        required fields are present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"address": {"zip_code": "10001"}, "age": 30}
        result = await Validator.validate(payload, _NestedPersonSchema)
        self.assertIsInstance(result, _NestedPersonSchema)
        self.assertEqual(result.address.zip_code, "10001")

    async def testInvalidNestedFieldRaisesValidationException(self) -> None:
        """Raise ValidationException when a nested field has the wrong type.

        Validates that type errors in nested schema fields propagate as
        ValidationException correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"address": {"zip_code": 12345}, "age": 30}
        with self.assertRaises(ValidationException):
            await Validator.validate(payload, _NestedPersonSchema)

    async def testValidatorErrorMethodReturnsDict(self) -> None:
        """Return a dict from ValidationException.error() for nested errors.

        Validates that the error() method surfaces a summary message and
        the dotted field path of failures in nested schema fields.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"address": {"zip_code": 99}, "age": 1}
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate(payload, _NestedPersonSchema)
        err = ctx.exception.error()
        self.assertIn("message", err)
        self.assertIn("errors", err)
        self.assertIn("address.zip_code", err["errors"])

class TestValidatorMultipleErrors(TestCase):

    async def testEveryInvalidFieldIsReported(self) -> None:
        """Report every invalid field instead of stopping at the first one.

        Validates that a payload breaking two constraints produces one
        entry per offending field.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate({"score": 500, "tag": "x"}, _ConstrainedSchema)
        self.assertEqual(
            set(ctx.exception.errors.keys()),
            {"score", "tag"},
        )

    async def testMissingFieldsAreAllReported(self) -> None:
        """Report every missing required field at once.

        Validates that an empty payload lists all required fields rather
        than only the first one detected by msgspec.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate({}, _PersonSchema)
        self.assertEqual(set(ctx.exception.errors.keys()), {"name", "age"})

    async def testNestedAndRootErrorsAreCombined(self) -> None:
        """Combine nested schema errors with root-level errors.

        Validates that failures inside a nested schema are reported with a
        dotted path alongside failures of the parent schema.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"address": {"zip_code": 99}, "age": "old"}
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate(payload, _NestedPersonSchema)
        self.assertEqual(
            set(ctx.exception.errors.keys()),
            {"address.zip_code", "age"},
        )

    async def testMessagesAreListsOfStrings(self) -> None:
        """Expose every field error as a list of message strings.

        Validates the response contract consumed by the HTTP layer, where
        each field maps to an array of messages.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate({"name": 1, "age": "x"}, _PersonSchema)
        for messages in ctx.exception.errors.values():
            self.assertIsInstance(messages, list)
            for message in messages:
                self.assertIsInstance(message, str)

    async def testCustomRulesRunWhenAnotherFieldFailsConversion(self) -> None:
        """Run custom rules even when a sibling field breaks a constraint.

        Validates that a rule such as ``Email`` still reports its failure
        when msgspec aborts the whole-payload conversion because of another
        field.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"email": "not-an-email", "password": "123"}
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate(payload, _CredentialsSchema)
        self.assertEqual(
            set(ctx.exception.errors.keys()),
            {"email", "password"},
        )

    async def testCustomRuleIsSkippedWhenItsOwnFieldIsInvalid(self) -> None:
        """Skip a custom rule when its own field failed conversion.

        Validates that only the constraint failure is reported, since the
        rule has no converted value to inspect.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"email": "a@b", "password": "12345678"}
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate(payload, _CredentialsSchema)
        messages = ctx.exception.errors["email"]
        self.assertEqual(len(messages), 1)
        self.assertNotIn("email address", messages[0])

class TestValidatorGreaterThan(TestCase):

    async def testGreaterThanIsEnforced(self) -> None:
        """Raise ValidationException when a GreaterThan constraint is violated.

        Validates that a value equal to the lower bound is rejected by
        the exclusive GreaterThan constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _GtSchema(Schema):
            n: Annotated[int, GreaterThan(0)]

        with self.assertRaises(ValidationException):
            await Validator.validate({"n": 0}, _GtSchema)

    async def testGreaterThanAcceptsValueAboveBound(self) -> None:
        """Accept a value strictly above the GreaterThan lower bound.

        Validates that a value of 1 satisfies GreaterThan(0).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _GtSchema(Schema):
            n: Annotated[int, GreaterThan(0)]

        result = await Validator.validate({"n": 1}, _GtSchema)
        self.assertEqual(result.n, 1)

    async def testLessThanIsEnforced(self) -> None:
        """Raise ValidationException when a LessThan constraint is violated.

        Validates that a value equal to the upper bound is rejected by
        the exclusive LessThan constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _LtSchema(Schema):
            n: Annotated[int, LessThan(10)]

        with self.assertRaises(ValidationException):
            await Validator.validate({"n": 10}, _LtSchema)

class TestValidatorWithPlainStruct(TestCase):

    async def testPlanIsBuiltForAStructWithoutAPrebuiltPlan(self) -> None:
        """Validate a struct that the schema metaclass never processed.

        Validates that the validation plan is built on demand instead of
        assuming the class was prepared at definition time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await Validator.validate({"label": "raw"}, _PlainStruct)
        self.assertIsInstance(result, _PlainStruct)
        self.assertEqual(result.label, "raw")

    async def testNonMappingPayloadRaisesValidationException(self) -> None:
        """Raise ValidationException when the payload is not a mapping.

        Validates that the original conversion error is still reported
        when no declared field can be blamed for it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate([1, 2], _PersonSchema)
        self.assertEqual(len(ctx.exception.failures), 1)
