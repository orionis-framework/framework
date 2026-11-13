# ruff: noqa: PT009, PT027, TC001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Schema metadata is evaluated at runtime.
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID
from orionis.schemas import Schema
from orionis.schemas.constraints import GreaterThanOrEqual, MultipleOf
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase


class _Output(Schema, rename="camel"):
    item_count: Field[int, GreaterThanOrEqual(1)]


class TestInstanceValidation(TestCase):
    async def testMutatedNestedInstancesAreRevalidated(self) -> None:
        """
        Revalidate child instances mutated after construction.

        Returns
        -------
        None
            No return value.
        """

        class Batch(Schema):
            children: dict[str, list[_Output]]

        child = _Output(2)
        child.item_count = -1
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(Batch({"primary": [child]}), Batch)
        self.assertIn("children['primary'][0].itemCount", caught.exception.errors)

    async def testOmittedDefaultsAreStillValidated(self) -> None:
        """
        Validate default values even when serialization omits them.

        Returns
        -------
        None
            No return value.
        """

        class InvalidDefault(Schema, omit_defaults=True):
            count: Field[int, GreaterThanOrEqual(1)] = 0

        with self.assertRaises(ValidationException):
            await Validator.validate(InvalidDefault(), InvalidDefault)

    async def testNativeValuesArePreserved(self) -> None:
        """
        Preserve native leaf values when revalidating a schema instance.

        Returns
        -------
        None
            No return value.
        """

        class Native(Schema):
            timestamp: datetime
            amount: Decimal
            identifier: UUID
            binary: bytes

        original = Native(datetime.now(UTC), Decimal("1.25"), UUID(int=1), b"raw")
        validated = await Validator.validate(original, Native)
        self.assertEqual(validated, original)

    async def testNativeValuesAreNotCoercedIntoStrings(self) -> None:
        """
        Reject native values assigned to string fields.

        Returns
        -------
        None
            No return value.
        """

        class Text(Schema):
            value: str

        for value in (datetime.now(UTC), UUID(int=1), b"raw"):
            with self.assertRaises(ValidationException):
                await Validator.validate(Text(value), Text)

    async def testTaggedArraySchemasRetainWireShape(self) -> None:
        """
        Preserve tagged array representation during instance validation.

        Returns
        -------
        None
            No return value.
        """

        class Row(Schema, array_like=True, tag="row"):
            count: Field[int, GreaterThanOrEqual(1)]

        self.assertEqual(await Validator.validate(Row(3), Row), Row(3))
        with self.assertRaises(ValidationException):
            await Validator.validate(Row(0), Row)

    async def testArraySchemasReportEveryFieldConstraint(self) -> None:
        """
        Collect complete diagnostics from root and nested array schemas.

        Returns
        -------
        None
            No return value.
        """

        class Row(Schema, array_like=True, tag="row"):
            count: Field[int, GreaterThanOrEqual(2), MultipleOf(2)]
            other: int

        class Envelope(Schema):
            row: Row

        for payload, target, prefix in (
            (Row(1, "bad"), Row, ""),
            (Envelope(Row(1, "bad")), Envelope, "row."),
        ):
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate(payload, target)
            self.assertEqual(
                set(caught.exception.errors),
                {
                    prefix + "count",
                    prefix + "other",
                },
            )
            self.assertEqual(
                [error["rule"] for error in caught.exception.errors[prefix + "count"]],
                ["ge", "multiple_of"],
            )
