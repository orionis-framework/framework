# ruff: noqa: FBT003, PT009, PT027, SLF001, TC003
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep established public and external protocol names and signatures.
# Schema metadata is evaluated at runtime.
from collections.abc import Mapping, Sequence
from copy import deepcopy
from decimal import Decimal
import msgspec
from orionis.container.container import Container
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.base import BaseController
from orionis.http.enums import Interface
from orionis.http.request import Request
from orionis.schemas import Schema
from orionis.schemas.coercion import coerce_payload
from orionis.schemas.compiler import MetadataConflictError
from orionis.schemas.constraints import GreaterThan, MultipleOf
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.meta.validation import ValidationMetadata
from orionis.schemas.metadata import Coerce, Message
from orionis.schemas.rule import Rule
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

_PositiveInteger = Field[
    int,
    Coerce(),
    GreaterThan(0, message="Must be positive."),
    Message("Integer required."),
]


class _Quantity(Schema):
    quantity: _PositiveInteger


class _StrictQuantity(Schema):
    quantity: Field[int, GreaterThan(0)]


class _CoercionContainer(Container):
    __slots__ = ()


class _QuantityController(BaseController):
    async def __call__(self, payload: _Quantity) -> dict[str, int]:
        """
        Return a quantity validated by request dependency injection.

        Parameters
        ----------
        payload : _Quantity
            Converted controller input.

        Returns
        -------
        dict[str, int]
            Typed quantity received by the handler.
        """
        return {"quantity": payload.quantity}


class TestCoercion(TestCase):
    """Keep coercion opt-in and separate from structural and custom checks."""

    def testMarkerIsImmutableValidationMetadata(self) -> None:
        """Retain the marker after annotation compilation without instance state."""
        marker = Coerce()
        self.assertIsInstance(marker, ValidationMetadata)
        self.assertFalse(hasattr(marker, "__dict__"))
        with self.assertRaises(AttributeError):
            marker.enabled = True  # type: ignore[attr-defined]
        self.assertIn(marker, _Quantity.__orionis_meta__["quantity"])
        document = msgspec.json.schema(_Quantity)
        self.assertEqual(
            document["$defs"]["_Quantity"]["properties"]["quantity"]["type"],
            "integer",
        )

    def testDuplicateMarkersAreRejected(self) -> None:
        """Reject duplicate coercion metadata during schema declaration."""
        with self.assertRaises(MetadataConflictError):

            class Duplicate(Schema):
                quantity: Field[int, Coerce(), Coerce()]

    async def testNumericStringsProduceTypedValues(self) -> None:
        """Convert textual numbers before checking their numeric constraints."""
        for value in ("12", "12.0", 12):
            with self.subTest(value=value):
                payload = {"quantity": value}
                result = await Validator.validate(payload, _Quantity)
                self.assertEqual(result.quantity, 12)
                self.assertIs(type(result.quantity), int)
                self.assertIs(payload["quantity"], value)

    async def testCoercionRunsBeforeEveryConstraint(self) -> None:
        """Report all numeric failures rather than a string type mismatch."""

        class EvenQuantity(Schema):
            quantity: Field[
                int,
                GreaterThan(0, message="Positive."),
                Coerce(),
                MultipleOf(2, message="Even."),
            ]

        payload = {"quantity": "-3"}
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(payload, EvenQuantity)
        self.assertEqual(
            caught.exception.errors,
            {
                "quantity": [
                    {"rule": "gt", "message": "Positive."},
                    {"rule": "multiple_of", "message": "Even."},
                ],
            },
        )
        self.assertEqual(payload, {"quantity": "-3"})

    async def testInvalidValuesAreNotTruncatedOrDefaulted(self) -> None:
        """Keep incompatible input as a type error with its custom message."""
        for value in ("abc", "", "0012", "1.5", 1.5, None, True, [], {}):
            with self.subTest(value=value):
                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate({"quantity": value}, _Quantity)
                self.assertEqual(
                    caught.exception.errors,
                    {
                        "quantity": [{"rule": "type", "message": "Integer required."}],
                    },
                )

    async def testMissingValuesRemainMissing(self) -> None:
        """Do not synthesize a default for an omitted coercible field."""
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({}, _Quantity)
        self.assertEqual(caught.exception.failures[0].rule, "missing")

    async def testOtherNativeTargetTypesAreSupported(self) -> None:
        """Use declared float, boolean and decimal types without Python truthiness."""

        class Values(Schema):
            price: Field[float, Coerce(), GreaterThan(0)]
            enabled: Field[bool, Coerce()]
            amount: Field[Decimal, Coerce()]

        result = await Validator.validate(
            {
                "price": "12.5",
                "enabled": "false",
                "amount": "12.50",
            },
            Values,
        )
        self.assertEqual(result.price, 12.5)
        self.assertIs(type(result.price), float)
        self.assertIs(result.enabled, False)
        self.assertEqual(result.amount, Decimal("12.50"))
        self.assertIsInstance(result.amount, Decimal)

    async def testUnmarkedSchemasAndSiblingsRemainStrict(self) -> None:
        """Do not enable coercion outside the marked annotation."""
        payload = {"quantity": "12"}
        self.assertIs(coerce_payload(payload, _StrictQuantity), payload)
        with self.assertRaises(ValidationException):
            await Validator.validate(payload, _StrictQuantity)

        class Mixed(Schema):
            coerced: Field[int, Coerce()]
            strict: int

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"coerced": "12", "strict": "12"}, Mixed)
        self.assertEqual(set(caught.exception.errors), {"strict"})

    async def testRulesSeeConvertedValuesAndSiblingsOnBothPaths(self) -> None:
        """Supply typed rule arguments even when another field fails conversion."""
        seen: list[tuple[object, object]] = []

        class Ordered(Rule):
            __code__ = "ordered"
            __message__ = "Below minimum."

            async def enforce(
                self,
                _field: str,
                value: object,
                instance: object,
            ) -> bool:
                """
                Compare converted values and record the rule context.

                Parameters
                ----------
                _field : str
                    Unused field path.
                value : object
                    Converted field value.
                instance : object
                    Schema or recovered sibling namespace.

                Returns
                -------
                bool
                    Whether the value is at least the converted minimum.
                """
                minimum = getattr(instance, "minimum", None)
                seen.append((value, minimum))
                return (
                    isinstance(value, int)
                    and isinstance(minimum, int)
                    and value >= minimum
                )

        class Values(Schema):
            quantity: Field[int, Coerce(), GreaterThan(0), Ordered()]
            minimum: Field[int, Coerce()]
            other: int

        result = await Validator.validate(
            {
                "quantity": "12",
                "minimum": "2",
                "other": 1,
            },
            Values,
        )
        self.assertEqual(result.quantity, 12)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(
                {
                    "quantity": "0",
                    "minimum": "2",
                    "other": "bad",
                },
                Values,
            )
        self.assertEqual(
            [error["rule"] for error in caught.exception.errors["quantity"]],
            ["gt", "ordered"],
        )
        self.assertEqual(set(caught.exception.errors), {"quantity", "other"})
        self.assertEqual(seen, [(12, 2), (0, 2)])
        self.assertTrue(
            all(type(value) is int and type(minimum) is int for value, minimum in seen),
        )
        with self.assertRaises(ValidationException):
            await Validator.validate(
                {
                    "quantity": "bad",
                    "minimum": "2",
                    "other": 1,
                },
                Values,
            )
        self.assertEqual(len(seen), 2)

    async def testCollectionItemsUseTheirOwnMarkers(self) -> None:
        """Convert list, mapping, tuple and set values without changing input."""

        class Values(Schema):
            numbers: list[_PositiveInteger]
            by_name: dict[str, _PositiveInteger]
            pair: tuple[str, _PositiveInteger]
            variadic: tuple[_PositiveInteger, ...]
            unique: set[_PositiveInteger]
            frozen: frozenset[_PositiveInteger]

        payload = {
            "numbers": ["1", "2"],
            "by_name": {"primary": "3"},
            "pair": ["keep", "4"],
            "variadic": ["5", "6"],
            "unique": ["7"],
            "frozen": ["8"],
        }
        original = deepcopy(payload)
        result = await Validator.validate(payload, Values)
        self.assertEqual(result.numbers, [1, 2])
        self.assertEqual(result.by_name, {"primary": 3})
        self.assertEqual(result.pair, ("keep", 4))
        self.assertEqual(result.variadic, (5, 6))
        self.assertEqual(result.unique, {7})
        self.assertEqual(result.frozen, frozenset({8}))
        self.assertEqual(payload, original)

    async def testCollectionAliasesAreSupported(self) -> None:
        """Traverse supported abstract sequence and mapping annotations."""

        class Values(Schema):
            numbers: Sequence[_PositiveInteger]
            by_name: Mapping[str, _PositiveInteger]

        result = await Validator.validate(
            {
                "numbers": ["1"],
                "by_name": {"primary": "2"},
            },
            Values,
        )
        self.assertEqual(result.numbers, [1])
        self.assertEqual(result.by_name, {"primary": 2})

    async def testNestedSchemasAndPartialFailuresKeepTheirPaths(self) -> None:
        """Retain coercion and all errors through optional nested collections."""

        class Batch(Schema):
            primary: _Quantity | None
            grouped: dict[str, list[_Quantity]]

        payload = {
            "primary": {"quantity": "2"},
            "grouped": {"main": [{"quantity": "0"}, {"quantity": "bad"}]},
        }
        original = deepcopy(payload)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(payload, Batch)
        self.assertEqual(
            caught.exception.errors,
            {
                "grouped['main'][0].quantity": [
                    {"rule": "gt", "message": "Must be positive."},
                ],
                "grouped['main'][1].quantity": [
                    {"rule": "type", "message": "Integer required."},
                ],
            },
        )
        self.assertEqual(payload, original)
        result = await Validator.validate(
            {
                "primary": {"quantity": "2"},
                "grouped": {"main": [{"quantity": "3"}]},
            },
            Batch,
        )
        self.assertEqual(result.primary.quantity, 2)
        self.assertEqual(result.grouped["main"][0].quantity, 3)

    async def testCollectionMarkersApplyToValuesNotKeysOrSiblings(self) -> None:
        """Allow whole-value coercion while keeping dictionary keys strict."""

        class Values(Schema):
            numbers: Field[list[Field[int, GreaterThan(0)]], Coerce()]
            by_number: Field[dict[int, int], Coerce()]
            other: int = 1

        result = await Validator.validate(
            {
                "numbers": ["1", "2"],
                "by_number": {1: "2"},
            },
            Values,
        )
        self.assertEqual(result.numbers, [1, 2])
        self.assertEqual(result.by_number, {1: 2})
        with self.assertRaises(ValidationException):
            await Validator.validate(
                {
                    "numbers": ["1"],
                    "by_number": {"1": "2"},
                },
                Values,
            )
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(
                {
                    "numbers": ["0"],
                    "by_number": {1: "2"},
                    "other": "1",
                },
                Values,
            )
        self.assertEqual(set(caught.exception.errors), {"numbers[0]", "other"})
        self.assertEqual(caught.exception.errors["numbers[0]"][0]["rule"], "gt")

    async def testNestedSchemaMarkerEnablesOnlyItsSubtree(self) -> None:
        """Permit explicit coercion of a complete nested schema."""

        class Values(Schema):
            child: Field[_StrictQuantity, Coerce()]
            strict: int

        result = await Validator.validate(
            {
                "child": {"quantity": "12"},
                "strict": 1,
            },
            Values,
        )
        self.assertEqual(result.child.quantity, 12)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(
                {
                    "child": {"quantity": "0"},
                    "strict": "1",
                },
                Values,
            )
        self.assertEqual(set(caught.exception.errors), {"child.quantity", "strict"})
        self.assertEqual(caught.exception.errors["child.quantity"][0]["rule"], "gt")

    async def testNullableAnnotationsPreserveNoneAndConstraints(self) -> None:
        """Coerce both outer and branch markers without replacing null values."""

        class Outer(Schema):
            value: Field[int | None, Coerce()] = None

        class Branch(Schema):
            value: _PositiveInteger | None

        for schema in (Outer, Branch):
            for value, expected in ((None, None), ("2", 2)):
                with self.subTest(schema=schema, value=value):
                    result = await Validator.validate({"value": value}, schema)
                    self.assertEqual(result.value, expected)
        self.assertIsNone((await Validator.validate({}, Outer)).value)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"value": "0"}, Branch)
        self.assertEqual(caught.exception.errors["value"][0]["rule"], "gt")

    async def testUnionKeepsAnAlreadyCompatibleBranch(self) -> None:
        """Avoid turning a string into an integer when the union accepts strings."""

        class Branch(Schema):
            value: Field[int, Coerce()] | str

        class Outer(Schema):
            value: Field[int | str, Coerce()]

        for schema in (Branch, Outer):
            result = await Validator.validate({"value": "12"}, schema)
            self.assertEqual(result.value, "12")
            self.assertIs(type(result.value), str)

    async def testTaggedUnionsDoNotCoerceTheWrongBranch(self) -> None:
        """Respect schema discriminator tags before coercing nested fields."""

        class Coerced(Schema, tag="coerced", tag_field="kind"):
            quantity: _PositiveInteger

        class Strict(Schema, tag="strict", tag_field="kind"):
            quantity: int

        class Envelope(Schema):
            item: Coerced | Strict

        result = await Validator.validate(
            {
                "item": {"kind": "coerced", "quantity": "12"},
            },
            Envelope,
        )
        self.assertIsInstance(result.item, Coerced)
        self.assertEqual(result.item.quantity, 12)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(
                {
                    "item": {"kind": "strict", "quantity": "12"},
                },
                Envelope,
            )
        self.assertEqual(caught.exception.errors["item.quantity"][0]["rule"], "type")

    async def testUnionSelectionDoesNotRunSchemaHooksTwice(self) -> None:
        """Construct nested union members only during the final conversion."""
        calls: list[int] = []

        class Child(Schema):
            quantity: _PositiveInteger

            def __post_init__(self) -> None:
                """Record each construction of the converted child."""
                calls.append(self.quantity)

        class Parent(Schema):
            child: Child | None

        for quantity in (12, "12"):
            calls.clear()
            result = await Validator.validate(
                {
                    "child": {"quantity": quantity},
                },
                Parent,
            )
            self.assertEqual(result.child.quantity, 12)
            self.assertEqual(calls, [12])

    async def testTaggedArraySchemasUseEncodedNamesAndPositions(self) -> None:
        """Keep array tags outside the field positions used for coercion."""

        class Row(Schema, array_like=True, tag="row", rename="camel"):
            item_count: _PositiveInteger

        payload = ["row", "12"]
        result = await Validator.validate(payload, Row)
        self.assertEqual(result.item_count, 12)
        self.assertEqual(payload, ["row", "12"])
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(["row", "0"], Row)
        self.assertEqual(
            caught.exception.errors,
            {
                "itemCount": [{"rule": "gt", "message": "Must be positive."}],
            },
        )

    async def testInheritedRenamedFieldsKeepTheirMarkers(self) -> None:
        """Reuse coercion metadata after inheritance and field renaming."""

        class Parent(Schema, rename="camel"):
            item_count: _PositiveInteger

        class Child(Parent):
            other: int = 1

        result = await Validator.validate({"itemCount": "12"}, Child)
        self.assertEqual(result.item_count, 12)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"itemCount": "0"}, Child)
        self.assertEqual(set(caught.exception.errors), {"itemCount"})
        self.assertEqual(caught.exception.errors["itemCount"][0]["rule"], "gt")

    async def testExistingInstancesAreConvertedWithoutMutation(self) -> None:
        """Revalidate marked instances without weakening unmarked output schemas."""
        original = _Quantity("12")
        result = await Validator.validate(original, _Quantity)
        self.assertEqual(result.quantity, 12)
        self.assertEqual(original.quantity, "12")
        with self.assertRaises(ValidationException):
            await Validator.validate(_StrictQuantity("12"), _StrictQuantity)

    async def testMultipartRequestInjectionReceivesAnInteger(self) -> None:
        """Convert an actual multipart text field before invoking its controller."""
        body = (
            b'--coercion\r\nContent-Disposition: form-data; name="quantity"\r\n'
            b"\r\n12\r\n--coercion--\r\n"
        )

        async def receive() -> dict[str, object]:
            """
            Return the complete ASGI multipart body.

            Returns
            -------
            dict[str, object]
                Single terminal HTTP body event.
            """
            return {"type": "http.request", "body": body, "more_body": False}

        adapter = ASGITransportAdapter(
            {
                "type": "http",
                "method": "POST",
                "path": "/quantities",
                "scheme": "http",
                "query_string": b"",
                "server": ("localhost", 80),
                "headers": [
                    (b"content-type", b"multipart/form-data; boundary=coercion"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            },
        )
        request = Request(Interface.ASGI, adapter, receive_or_protocol=receive)
        data = await request.data()
        self.assertEqual(data, {"quantity": "12"})
        container = _CoercionContainer()
        try:
            async with container.beginScope():
                container.instance(Request, request)
                result = await container.invoke(_QuantityController().__call__)
            self.assertEqual(result, {"quantity": 12})
            self.assertIs(type(result["quantity"]), int)
            self.assertEqual(data, {"quantity": "12"})
        finally:
            Container._instances.pop(_CoercionContainer, None)
