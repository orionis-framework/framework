from array import array
from collections import deque
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.schemas import Schema
from orionis.schemas import constraints as constraints_module
from orionis.schemas import rules as rules_module
from orionis.schemas.exceptions import ValidationException
# Schema annotations resolve these imports at runtime.
from orionis.schemas.fields import Field  # noqa: TC001
from orionis.schemas.metadata import Coerce  # noqa: TC001
from orionis.schemas.rules.empty import Empty
from orionis.schemas.rules.measure import is_empty
from orionis.schemas.rules.no_empty import NoEmpty
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

_OWNER = object()

def _empty_values() -> tuple[object, ...]:
    """
    Create independent examples of every supported empty value category.

    Returns
    -------
    tuple[object, ...]
        Empty scalar, binary, numeric and collection values.
    """
    return (
        None, "", " ", "\t\r\n", "\u00a0",
        False, 0, 0.0, -0.0, 0j, Decimal(0), Decimal("-0.000"), Fraction(0),
        b"", bytearray(), memoryview(b""), [], (), {}, set(), frozenset(),
        range(0), deque(), array("i"), {}.keys(),
    )

def _present_values() -> tuple[object, ...]:
    """
    Create non-empty values, including containers whose only item is empty.

    Returns
    -------
    tuple[object, ...]
        Present scalar, binary, numeric and collection values.
    """
    return (
        "text", " text ", "0", "false", True, 1, -1, 0.5, 1j,
        Decimal("0.0001"), Decimal("1e-10000"),
        Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
        Fraction(1, 10**1000), float("nan"), float("inf"),
        b" ", bytearray(b"0"), memoryview(b"0"),
        [None], ("",), {"key": None}, {0}, frozenset({False}),
        range(1), deque([None]), array("i", [0]), {"key": None}.keys(),
        object(),
    )

class _EmptyValue(Schema):
    value: Field[object, Empty()]

class _PresentValue(Schema):
    value: Field[object, NoEmpty()]

class TestEmptyRules(TestCase):
    """Keep emptiness predicates complementary and independent of truthiness."""

    async def testEmptyAcceptsEveryEmptyCategory(self) -> None:
        """Accept None, blanks, zero, False and zero-length containers."""
        rule = Empty()
        for value in _empty_values():
            with self.subTest(value=value):
                self.assertIs(is_empty(value), True)
                self.assertIs(await rule.enforce("value", value, _OWNER), True)

    async def testEmptyRejectsEveryPresentCategory(self) -> None:
        """Reject populated values without recursively inspecting their contents."""
        rule = Empty()
        for value in _present_values():
            with self.subTest(value=value):
                self.assertIs(is_empty(value), False)
                self.assertIs(await rule.enforce("value", value, _OWNER), False)

    async def testNoEmptyIsTheExactInverse(self) -> None:
        """Return the opposite result for every supported input category."""
        empty = Empty()
        no_empty = NoEmpty()
        for value in (*_empty_values(), *_present_values()):
            with self.subTest(value=value):
                result = await empty.enforce("value", value, _OWNER)
                self.assertIs(
                    await no_empty.enforce("value", value, _OWNER), not result,
                )

    async def testSizedValuesDoNotEvaluateAmbiguousTruthiness(self) -> None:
        """Check array-like lengths without coercing the container to bool."""
        class AmbiguousList(list[object]):
            def __bool__(self) -> bool:
                """Reject attempts to evaluate container truthiness."""
                error_msg = "Container truthiness must not be evaluated."
                raise AssertionError(error_msg)

        for value, expected in (
            (AmbiguousList(), True), (AmbiguousList([0]), False),
        ):
            self.assertIs(await Empty().enforce("value", value, _OWNER), expected)
            self.assertIs(
                await NoEmpty().enforce("value", value, _OWNER), not expected,
            )

    async def testIteratorsAreNotConsumed(self) -> None:
        """Leave unsized iterators present without probing their contents."""
        for values in ([], [0]):
            iterator = iter(values)
            self.assertFalse(await Empty().enforce("value", iterator, _OWNER))
            self.assertTrue(await NoEmpty().enforce("value", iterator, _OWNER))
            self.assertEqual(list(iterator), values)

    async def testUploadedFilesUseTheirByteSize(self) -> None:
        """Recognize empty and disk-backed uploads without changing the file."""
        upload = UploadedFile(
            "payload.bin", "application/octet-stream", memory_threshold=1,
        )
        try:
            self.assertTrue(await Empty().enforce("file", upload, _OWNER))
            self.assertFalse(await NoEmpty().enforce("file", upload, _OWNER))
            upload.write(b"ab")
            self.assertFalse(await Empty().enforce("file", upload, _OWNER))
            self.assertTrue(await NoEmpty().enforce("file", upload, _OWNER))
            self.assertEqual(upload.size, 2)
            self.assertEqual(upload.read(), b"ab")
        finally:
            upload.close()

    async def testFileContentsAreNeverRead(self) -> None:
        """Use upload metadata without invoking even a failing file reader."""
        def read() -> bytes:
            """Reject unexpected reads while checking upload emptiness."""
            error_msg = "Emptiness checks must not read uploaded files."
            raise AssertionError(error_msg)

        for size in (0, 1):
            upload = SimpleNamespace(
                read=read, size=size, filename="payload.bin",
            )
            self.assertIs(
                await Empty().enforce("file", upload, _OWNER), size == 0,
            )
            self.assertIs(
                await NoEmpty().enforce("file", upload, _OWNER), size != 0,
            )

    async def testDefaultFailureCodesAndMessages(self) -> None:
        """Expose distinct stable codes through the shared rule interface."""
        for rule, value, code, message in (
            (Empty(), "text", "empty", "Value must be empty."),
            (NoEmpty(), None, "no_empty", "Value must not be empty."),
        ):
            failure = await rule.validate("payload.value", value, _OWNER)
            self.assertIsNotNone(failure)
            self.assertEqual(failure.field, "payload.value")
            self.assertEqual(failure.rule, code)
            self.assertEqual(failure.message, message)
        self.assertIsNone(await Empty().validate("value", "", _OWNER))
        self.assertIsNone(await NoEmpty().validate("value", "text", _OWNER))

    async def testCustomMessagesAndKeywordArgumentsArePreserved(self) -> None:
        """Keep message overrides and the public enforcement signature."""
        empty = Empty(message="Leave this blank.")
        no_empty = NoEmpty(message="Provide a value.")
        self.assertTrue(await empty.enforce(
            field="value", value=None, instance=_OWNER,
        ))
        self.assertTrue(await no_empty.enforce(
            field="value", value="text", instance=_OWNER,
        ))
        empty_failure = await empty.validate("value", "text", _OWNER)
        present_failure = await no_empty.validate("value", False, _OWNER)
        self.assertEqual(empty_failure.message, "Leave this blank.")
        self.assertEqual(empty_failure.rule, "empty")
        self.assertEqual(present_failure.message, "Provide a value.")
        self.assertEqual(present_failure.rule, "no_empty")

    def testBothPublicCatalogsExportTheSameRules(self) -> None:
        """Expose the rule classes through lazy and constraints imports."""
        for name, rule in (("Empty", Empty), ("NoEmpty", NoEmpty)):
            self.assertIn(name, rules_module.__all__)
            self.assertIn(name, constraints_module.__all__)
            self.assertIs(getattr(rules_module, name), rule)
            self.assertIs(getattr(constraints_module, name), rule)

    async def testValidatorAppliesBothRulesToTypedObjectValues(self) -> None:
        """Apply the agreed scalar and collection semantics through schemas."""
        for value in (None, " ", "\t", [], {}, 0, False):
            with self.subTest(value=value):
                result = await Validator.validate({"value": value}, _EmptyValue)
                self.assertEqual(result.value, value)
                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate({"value": value}, _PresentValue)
                self.assertEqual(caught.exception.errors, {
                    "value": [{
                        "rule": "no_empty", "message": "Value must not be empty.",
                    }],
                })
        for value in ("0", "text", [None], {"key": None}, True, 1):
            with self.subTest(value=value):
                result = await Validator.validate({"value": value}, _PresentValue)
                self.assertEqual(result.value, value)
                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate({"value": value}, _EmptyValue)
                self.assertEqual(caught.exception.failure.rule, "empty")

    async def testNullableFieldsStillRunTheRules(self) -> None:
        """Reject None with NoEmpty even when its declared type allows null."""
        class NullableValue(Schema):
            value: Field[str | None, NoEmpty()]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"value": None}, NullableValue)
        self.assertEqual(caught.exception.failure.rule, "no_empty")
        result = await Validator.validate({"value": "text"}, NullableValue)
        self.assertEqual(result.value, "text")

    async def testMissingFieldsAndWrongTypesRemainStructuralErrors(self) -> None:
        """Do not let emptiness checks bypass required fields or declared types."""
        for schema in (_EmptyValue, _PresentValue):
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate({}, schema)
            self.assertEqual(caught.exception.failure.rule, "missing")

        class IntegerValue(Schema):
            value: Field[int, Empty()]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"value": None}, IntegerValue)
        self.assertEqual(caught.exception.failure.rule, "type")

    async def testNestedAndSiblingFailuresKeepTheirMessagesAndPaths(self) -> None:
        """Run both rules on normal and partial conversion error paths."""
        class Child(Schema, rename="camel"):
            display_name: Field[str, NoEmpty(message="Name required.")]

        class Batch(Schema):
            children: list[Child]
            reserved: Field[list[int], Empty(message="Leave empty.")]
            other: int

        for other in (1, "bad"):
            payload = {
                "children": [{"displayName": " "}, {"displayName": ""}],
                "reserved": [0], "other": other,
            }
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate(payload, Batch)
            errors = caught.exception.errors
            for index in range(2):
                self.assertEqual(errors[f"children[{index}].displayName"], [{
                    "rule": "no_empty", "message": "Name required.",
                }])
            self.assertEqual(errors["reserved"], [{
                "rule": "empty", "message": "Leave empty.",
            }])
            self.assertEqual("other" in errors, other == "bad")
            self.assertEqual(payload["reserved"], [0])
            self.assertEqual(payload["children"][0]["displayName"], " ")

        result = await Validator.validate({
            "children": [{"displayName": " Ada "}], "reserved": [], "other": 1,
        }, Batch)
        self.assertEqual(result.children[0].display_name, " Ada ")

    async def testCoercionPrecedesEmptinessRules(self) -> None:
        """Check numeric zero after casting without treating the string as zero."""
        class EmptyCount(Schema):
            quantity: Field[int, Coerce(), Empty()]

        class RequiredCount(Schema):
            quantity: Field[int, Coerce(), NoEmpty()]

        self.assertEqual(
            (await Validator.validate({"quantity": "0"}, EmptyCount)).quantity,
            0,
        )
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"quantity": "0"}, RequiredCount)
        self.assertEqual(caught.exception.failure.rule, "no_empty")
        self.assertEqual(
            (await Validator.validate({"quantity": "2"}, RequiredCount)).quantity,
            2,
        )
        self.assertEqual(
            (await Validator.validate({"value": "0"}, _PresentValue)).value, "0",
        )

    async def testCombiningBothRulesFailsExactlyOneCheck(self) -> None:
        """Keep the rules exact opposites when declared on the same field."""
        class OppositeRules(Schema):
            value: Field[object, Empty(), NoEmpty()]

        for value, code in ((None, "no_empty"), ("text", "empty")):
            with self.assertRaises(ValidationException) as caught:
                await Validator.validate({"value": value}, OppositeRules)
            self.assertEqual(
                [failure.rule for failure in caught.exception.failures], [code],
            )
