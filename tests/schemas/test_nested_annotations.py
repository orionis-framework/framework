from typing import Any, ClassVar
from orionis.schemas.compiler import MetadataConflictError
from orionis.schemas.constraints import (
    GreaterThanOrEqual,
    MaxLength,
    MinLength,
    MultipleOf,
    Pattern,
)
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.fields import Field, Nullable
from orionis.schemas.metadata import Message  # noqa: TC001
from orionis.schemas.rule import Rule
from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

_PositiveEven = Field[
    int,
    GreaterThanOrEqual(1, message="Positive required."),
    MultipleOf(2, message="Even required."),
]

class _ListValues(Schema):
    values: list[_PositiveEven]

class _MappingValues(Schema):
    values: dict[str, _PositiveEven]

class _TupleValues(Schema):
    values: tuple[str, _PositiveEven]

class _NullableValue(Schema):
    value: Nullable[_PositiveEven]

class _UnionValue(Schema):
    value: _PositiveEven | None

class _WrappedUnionValue(Schema):
    value: Field[Nullable[_PositiveEven], Message("Integer or None required.")]

class _BranchValue(Schema):
    value: (
        Field[int, GreaterThanOrEqual(4), MultipleOf(2)]
        | Field[str, MinLength(4), Pattern("^[A-Z]+$")]
    )

class _DistinctMessages(Schema):
    first: list[Field[int, GreaterThanOrEqual(1, message="First positive.")]]
    second: list[Field[int, GreaterThanOrEqual(1, message="Second positive.")]]

class _TypedValues(Schema):
    values: list[Field[int, Message("Integer required.")]]

class _UnhashableRule(Rule):
    __code__ = "custom"
    __message__ = "Custom rule failed."
    __hash__: ClassVar[Any] = None

    def __eq__(self, other: object) -> bool:
        """
        Compare rule instances without providing a hash implementation.

        Parameters
        ----------
        other : object
            Value to compare against this rule.

        Returns
        -------
        bool
            Whether the other object is an instance of this rule class.
        """
        return isinstance(other, _UnhashableRule)

    async def enforce(self, _field: str, _value: object, _instance: object) -> bool:
        """
        Reject a value to exercise unhashable rule metadata.

        Parameters
        ----------
        _field : str
            Unused field name.
        _value : object
            Unused value under validation.
        _instance : object
            Unused schema instance.

        Returns
        -------
        bool
            Always return False.
        """
        return False

class _UnhashableMetadata(Schema):
    value: Field[int, GreaterThanOrEqual(1), _UnhashableRule()]

class TestNestedAnnotations(TestCase):
    """Keep native constraints effective wherever their types are declared."""

    async def testCollectionItemsReportEveryConstraintAndLocalMessage(self) -> None:
        """
        Validate collection items with complete paths and local messages.

        Returns
        -------
        None
            Assert list, mapping and tuple items report both native constraints.
        """
        for schema, payload, field in (
            (_ListValues, {"values": [-1]}, "values[0]"),
            (_MappingValues, {"values": {"primary": -1}}, "values['primary']"),
            (_TupleValues, {"values": ["first", -1]}, "values[1]"),
        ):
            with self.subTest(schema=schema):
                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate(payload, schema)
                self.assertEqual(caught.exception.errors, {
                    field: [
                        {"rule": "ge", "message": "Positive required."},
                        {"rule": "multiple_of", "message": "Even required."},
                    ],
                })

    async def testValidCollectionsConvertNormally(self) -> None:
        """
        Accept collection items that satisfy every compiled constraint.

        Returns
        -------
        None
            Assert valid list, mapping and tuple values are preserved.
        """
        for schema, values in (
            (_ListValues, [2, 4]),
            (_MappingValues, {"primary": 2}),
            (_TupleValues, ("first", 2)),
        ):
            instance = await Validator.validate({"values": values}, schema)
            self.assertEqual(instance.values, values)

    async def testNullableBranchesKeepTheirConstraints(self) -> None:
        """
        Permit None while validating constraints on non-null union values.

        Returns
        -------
        None
            Assert nullable declarations retain every constraint and message.
        """
        for schema in (_NullableValue, _UnionValue, _WrappedUnionValue):
            for value in (None, 2):
                instance = await Validator.validate({"value": value}, schema)
                self.assertEqual(instance.value, value)
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate({"value": -1}, schema)
            self.assertEqual(caught.exception.errors["value"], [
                {"rule": "ge", "message": "Positive required."},
                {"rule": "multiple_of", "message": "Even required."},
            ])

    async def testUnionReportsOnlyTheMatchingBranchesConstraints(self) -> None:
        """
        Report only constraints belonging to the compatible union branch.

        Returns
        -------
        None
            Assert integer and string failures retain their own rule codes.
        """
        for value, codes in (
            (3, ["ge", "multiple_of"]), ("a", ["pattern", "min_length"]),
        ):
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate({"value": value}, _BranchValue)
            self.assertEqual([item.rule for item in caught.exception.failures], codes)
        for value in (8, "OKAY"):
            instance = await Validator.validate({"value": value}, _BranchValue)
            self.assertEqual(instance.value, value)

    async def testEqualConstraintsKeepDistinctMessages(self) -> None:
        """
        Keep field-specific messages distinct for equal constraints.

        Returns
        -------
        None
            Assert annotation caching preserves each field message.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"first": [0], "second": [0]}, _DistinctMessages)
        self.assertEqual(caught.exception.errors, {
            "first[0]": [{"rule": "ge", "message": "First positive."}],
            "second[0]": [{"rule": "ge", "message": "Second positive."}],
        })

    async def testItemTypeMessagesArePreserved(self) -> None:
        """
        Apply local type messages to individual collection items.

        Returns
        -------
        None
            Assert the invalid item uses its declared Message metadata.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"values": ["bad"]}, _TypedValues)
        self.assertEqual(caught.exception.errors, {
            "values[0]": [{"rule": "type", "message": "Integer required."}],
        })

    async def testUnhashableMetadataCanCollectConstraintFailures(self) -> None:
        """
        Collect failures when custom rule metadata is unhashable.

        Returns
        -------
        None
            Assert both native and custom rule codes survive plan caching.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"value": -1}, _UnhashableMetadata)
        self.assertEqual(
            [item.rule for item in caught.exception.failures], ["ge", "custom"],
        )

    def testNestedConstraintConflictsFailDuringClassCreation(self) -> None:
        """
        Reject contradictory item constraints during schema declaration.

        Returns
        -------
        None
            Assert incompatible length bounds raise MetadataConflictError.
        """
        with self.assertRaises(MetadataConflictError):
            class Invalid(Schema):
                values: list[Field[str, MinLength(4), MaxLength(1)]]

    def testInnerRulesFailWithActionableConfigurationError(self) -> None:
        """
        Reject unsupported inner rules with actionable configuration errors.

        Returns
        -------
        None
            Assert collection and union declarations identify supported alternatives.
        """
        with self.assertRaisesRegex(TypeError, "Use a child Schema"):
            class InvalidItems(Schema):
                values: list[Field[int, _UnhashableRule()]]
        with self.assertRaisesRegex(TypeError, "outer Field"):
            class InvalidBranch(Schema):
                value: Field[int, _UnhashableRule()] | None
