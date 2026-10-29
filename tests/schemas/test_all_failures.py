# Schema metadata is evaluated at runtime.
# ruff: noqa: TC001
from datetime import UTC, datetime
import msgspec
from orionis.schemas import Schema
from orionis.schemas.constraints import (
    ConfirmPassword, Email, GreaterThan, GreaterThanOrEqual, MinLength,
    MultipleOf, Pattern, TimezoneAware, TimezoneNaive,
)
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

class _Order(Schema):
    quantity: Field[
        int, GreaterThanOrEqual(1, message="Quantity must be positive."),
        MultipleOf(2, message="Quantity must be even."),
    ]
    email: Field[
        str, MinLength(5, message="Email is too short."),
        Email(message="Email is invalid."),
    ]

class _Child(Schema):
    code: Field[str, MinLength(4, message="Too short."), Pattern("^[A-Z]+$")]

class TestAllFailures(TestCase):
    async def testAllConstraintsAndRulesOnEachField(self) -> None:
        """
        Collect every applicable failure and count them in the summary.

        Returns
        -------
        None
            Assert four structured failures across two fields.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"quantity": -3, "email": "x"}, _Order)
        error = caught.exception
        self.assertEqual(error.errors["quantity"], [
            {"rule": "ge", "message": "Quantity must be positive."},
            {"rule": "multiple_of", "message": "Quantity must be even."},
        ])
        self.assertEqual(error.errors["email"], [
            {"rule": "min_length", "message": "Email is too short."},
            {"rule": "email", "message": "Email is invalid."},
        ])
        self.assertEqual(
            error.message, "Quantity must be positive. (and 3 more errors)",
        )

    async def testWrongTypesDoNotRunValueRules(self) -> None:
        """
        Skip value rules when a field has an incompatible type.

        Returns
        -------
        None
            Assert that each incompatible field reports only its type error.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"quantity": "wrong", "email": 3}, _Order)
        self.assertEqual(
            {key: [error["rule"] for error in errors]
             for key, errors in caught.exception.errors.items()},
            {"quantity": ["type"], "email": ["type"]},
        )

    async def testNativeOnlyChildrenStillEnforceConstraints(self) -> None:
        """
        Preserve native child validation when empty rule plans are pruned.

        Returns
        -------
        None
            Assert valid children pass and invalid children report both constraints.
        """
        class Batch(Schema):
            children: list[_Child]

        result = await Validator.validate({"children": [{"code": "ABCD"}]}, Batch)
        self.assertEqual(result.children[0].code, "ABCD")
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"children": [{"code": "a"}]}, Batch)
        self.assertEqual(len(caught.exception.errors["children[0].code"]), 2)

    async def testNestedCollectionsKeepEveryChildConstraint(self) -> None:
        """
        Retain container and child failures at their respective paths.

        Returns
        -------
        None
            Assert collection length and both child constraints are reported.
        """
        class Batch(Schema):
            children: Field[list[_Child], MinLength(3, message="Need three.")]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(
                {"children": [{"code": "a"}, {"code": "b"}]}, Batch,
            )
        self.assertEqual(set(caught.exception.errors), {
            "children", "children[0].code", "children[1].code",
        })
        self.assertEqual(caught.exception.errors["children"], [
            {"rule": "min_length", "message": "Need three."},
        ])
        for path in ("children[0].code", "children[1].code"):
            self.assertEqual(
                {error["rule"] for error in caught.exception.errors[path]},
                {"min_length", "pattern"},
            )
            self.assertIn(
                {"rule": "min_length", "message": "Too short."},
                caught.exception.errors[path],
            )

    async def testPrimitiveCollectionReportsAllBadElements(self) -> None:
        """
        Enumerate constraint failures in every primitive collection element.

        Returns
        -------
        None
            Assert both invalid elements report both native constraints.
        """
        class Numbers(Schema):
            values: list[Field[int, msgspec.Meta(ge=1, multiple_of=2)]]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"values": [-3, -5]}, Numbers)
        self.assertEqual(set(caught.exception.errors), {"values[0]", "values[1]"})
        for details in caught.exception.errors.values():
            self.assertEqual(
                [error["rule"] for error in details], ["ge", "multiple_of"],
            )

    async def testDeclaredExclusiveCodeSurvivesIntegerNormalization(self) -> None:
        """
        Preserve declared exclusive-bound codes during integer validation.

        Returns
        -------
        None
            Assert the failure retains its ``gt`` code and custom message.
        """
        class Exclusive(Schema):
            quantity: Field[int, GreaterThan(0, message="Positive.")]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"quantity": 0}, Exclusive)
        self.assertEqual(caught.exception.errors["quantity"], [
            {"rule": "gt", "message": "Positive."},
        ])

    async def testRenamedInheritedFieldsKeepMessagesAndRulePaths(self) -> None:
        """
        Preserve inherited messages and encoded paths across validation routes.

        Returns
        -------
        None
            Assert rule and constraint failures use the renamed field.
        """
        class Parent(Schema, rename="camel"):
            email_address: Field[str, MinLength(5, message="Too short."), Email()]

        class Child(Parent):
            count: int = 1

        for payload in ({"emailAddress": "badmail"}, {"emailAddress": "x"}):
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate(payload, Child)
            self.assertEqual(set(caught.exception.errors), {"emailAddress"})
        self.assertIn(
            {"rule": "min_length", "message": "Too short."},
            caught.exception.errors["emailAddress"],
        )

    async def testFallbackRulesSeeDefaultsAndPythonAttributeNames(self) -> None:
        """
        Preserve sibling context after a field fails type conversion.

        Returns
        -------
        None
            Assert cross-field rules can read defaults by Python attribute name.
        """
        class Credentials(Schema, rename="camel"):
            count: int
            password_confirmation: Field[str, ConfirmPassword("password_value")]
            password_value: str = "secret"  # noqa: S105

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "count": "bad", "passwordConfirmation": "different",
            }, Credentials)
        self.assertEqual(
            set(caught.exception.errors), {"count", "passwordConfirmation"},
        )

    async def testNullableConstraintsAcceptNone(self) -> None:
        """
        Allow None while validating constraints on non-null values.

        Returns
        -------
        None
            Assert null values pass and invalid integers report both constraints.
        """
        class OptionalNumber(Schema):
            value: Field[int, msgspec.Meta(ge=1, multiple_of=2)] | None
            count: int

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"value": None, "count": "bad"}, OptionalNumber)
        self.assertEqual(set(caught.exception.errors), {"count"})

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"value": -3, "count": 1}, OptionalNumber)
        self.assertEqual(
            [error["rule"] for error in caught.exception.errors["value"]],
            ["ge", "multiple_of"],
        )

    async def testTimezoneConstraintsKeepTheirCodesAndMessages(self) -> None:
        """
        Preserve both timezone constraint codes and their local messages.

        Returns
        -------
        None
            Assert invalid timezones fail independently and valid values pass.
        """
        class Event(Schema):
            aware: Field[datetime, TimezoneAware(message="Timezone required.")]
            naive: Field[datetime, TimezoneNaive(message="Timezone not allowed.")]

        naive = datetime(2026, 1, 1)
        aware = naive.replace(tzinfo=UTC)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"aware": naive, "naive": aware}, Event)
        self.assertEqual(caught.exception.errors, {
            "aware": [{"rule": "tz_aware", "message": "Timezone required."}],
            "naive": [{"rule": "tz_naive", "message": "Timezone not allowed."}],
        })
        result = await Validator.validate({"aware": aware, "naive": naive}, Event)
        self.assertEqual((result.aware, result.naive), (aware, naive))

    async def testFallbackRulesSeeFactoryDefaultsAndMissingFields(self) -> None:
        """
        Resolve factory defaults before running rules on incomplete payloads.

        Returns
        -------
        None
            Assert sibling rules pass while invalid or missing fields fail.
        """
        class Credentials(Schema):
            count: int
            password_confirmation: Field[str, ConfirmPassword("password_value")]
            password_value: str = msgspec.field(default_factory=lambda: "secret")

        for payload, code in (
            ({"count": "bad", "password_confirmation": "secret"}, "type"),
            ({"password_confirmation": "secret"}, "missing"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate(payload, Credentials)
                self.assertEqual(set(caught.exception.errors), {"count"})
                self.assertEqual(caught.exception.errors["count"][0]["rule"], code)
