from typing import Annotated
import msgspec
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.failure_collector import (
    FailureCollector,
    _field_plan,
    _nested_schema,
)
from orionis.schemas.metadata import Title
from orionis.schemas.rule import Rule
from orionis.schemas.schema import Schema
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Rule and schema fixtures
# ---------------------------------------------------------------------------

class _RejectRule(Rule):
    """Rule rejecting every value it inspects."""

    __code__ = "reject"
    __message__ = "Rejected."

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        """
        Reject every value.

        Parameters
        ----------
        _field : str
            Field name associated with the value.
        _value : object
            Value under validation.
        _instance : object
            Owner of the field value.

        Returns
        -------
        bool
            Always ``False``.
        """
        return False

class _Address(Schema):
    zip_code: str

class _RuledAddress(Schema):
    code: Annotated[str, _RejectRule()]

class _Person(Schema):
    name: str
    age: int

class _PartialDefaults(Schema):
    age: int
    label: str = "default"

class _OptionalNested(Schema):
    address: _Address | None

class _NestedParent(Schema):
    child: _RuledAddress
    count: int

class _RuledParent(Schema):
    code: Annotated[str, _RejectRule()]
    count: int

def _conversion_error(payload: object, schema: type) -> msgspec.ValidationError:
    """
    Return the error raised while converting a payload into a schema.

    Parameters
    ----------
    payload : object
        Raw input expected to be rejected by the conversion.
    schema : type
        Schema class the payload is converted against.

    Returns
    -------
    msgspec.ValidationError
        Error raised by the whole-payload conversion.

    Raises
    ------
    AssertionError
        If the payload converts successfully.
    """
    try:
        msgspec.convert(payload, type=schema)
    except msgspec.ValidationError as exc:
        return exc
    error_msg = "The payload converted without raising a validation error."
    raise AssertionError(error_msg)

def _uncached_struct(name: str, meta: dict[str, list[object]] | None = None) -> type:
    """
    Build a struct that mimics a schema without a cached validation plan.

    Parameters
    ----------
    name : str
        Class name given to the generated struct.
    meta : dict[str, list[object]] | None
        Orionis metadata attached to the struct, keyed by field name.

    Returns
    -------
    type
        Freshly created struct class absent from every plan cache.
    """
    klass = msgspec.defstruct(name, [("code", str)])
    klass.__orionis_meta__ = {} if meta is None else meta
    return klass

class TestNestedSchema(TestCase):

    def testBareSchemaIsReturned(self) -> None:
        """
        Return the schema declared directly by a field annotation.

        Validates the marker attribute lookup used to detect schemas.
        """
        self.assertIs(_nested_schema(_Address), _Address)

    def testAnnotatedWrapperIsUnwrapped(self) -> None:
        """
        Return the schema wrapped inside an Annotated alias.

        Validates that metadata never hides the wrapped schema.
        """
        self.assertIs(_nested_schema(Annotated[_Address, Title("A")]), _Address)

    def testUnionMemberIsReturned(self) -> None:
        """
        Return the schema declared as a union member.

        Validates support for optional nested schemas.
        """
        self.assertIs(_nested_schema(_Address | None), _Address)

    def testUnionWithoutSchemaReturnsNone(self) -> None:
        """
        Return None when no union member declares a schema.

        Validates that scalar unions are left untouched.
        """
        self.assertIsNone(_nested_schema(int | str))

    def testScalarAnnotationReturnsNone(self) -> None:
        """
        Return None for annotations carrying no schema.

        Validates the fallback applied to plain field types.
        """
        self.assertIsNone(_nested_schema(str))

class TestFieldPlan(TestCase):

    def testPlanIsCachedPerSchema(self) -> None:
        """
        Return the very same plan object on repeated calls.

        Validates the per-schema cache used on the error path.
        """
        self.assertIs(_field_plan(_Person), _field_plan(_Person))

    def testPlanDescribesEveryDeclaredField(self) -> None:
        """
        Describe name, requiredness and nesting for each declared field.

        Validates the tuple layout consumed by the collector.
        """
        entries = {entry[0]: entry for entry in _field_plan(_PartialDefaults)}
        self.assertEqual(set(entries), {"age", "label"})
        self.assertTrue(entries["age"][2])
        self.assertFalse(entries["label"][2])
        self.assertIsNone(entries["age"][3])

    def testNestedSchemaIsRecordedInThePlan(self) -> None:
        """
        Record the nested schema declared by a field.

        Validates that nested traversal metadata reaches the collector.
        """
        entries = {entry[0]: entry for entry in _field_plan(_OptionalNested)}
        self.assertIs(entries["address"][3], _Address)

    def testRulesAreBoundToTheirField(self) -> None:
        """
        Bind the custom rule validators declared for a field.

        Validates that rules are reused from the executor plan.
        """
        entries = {entry[0]: entry for entry in _field_plan(_RuledParent)}
        self.assertEqual(len(entries["code"][4]), 1)
        self.assertEqual(entries["count"][4], ())

    def testRulePlanIsBuiltWhenNotCached(self) -> None:
        """
        Build the rule plan when the schema has no cached entry.

        Validates the cache-miss branch of the plan builder.
        """
        klass = _uncached_struct("_FieldPlanColdRules", {"code": [_RejectRule()]})
        entries = {entry[0]: entry for entry in _field_plan(klass)}
        self.assertEqual(len(entries["code"][4]), 1)

class TestFailureCollectorCollect(TestCase):

    def testEveryMissingRequiredFieldIsReported(self) -> None:
        """
        Report each required field absent from the payload.

        Validates that reporting does not stop at the first missing field.
        """
        error = _conversion_error({}, _Person)
        failures = FailureCollector.collect({}, _Person, error)
        self.assertEqual({f.field for f in failures}, {"name", "age"})
        self.assertEqual({f.rule for f in failures}, {"missing"})

    def testOptionalMissingFieldIsIgnored(self) -> None:
        """
        Skip fields that are absent but carry a default value.

        Validates that defaults never produce a missing-field failure.
        """
        payload = {"age": "not-an-int"}
        error = _conversion_error(payload, _PartialDefaults)
        failures = FailureCollector.collect(payload, _PartialDefaults, error)
        self.assertEqual([f.field for f in failures], ["age"])

    def testNonMappingPayloadKeepsTheOriginalError(self) -> None:
        """
        Keep the parsed original error when no field can be blamed.

        Validates the fallback used for payloads that are not mappings.
        """
        payload = [1, 2]
        error = _conversion_error(payload, _Person)
        failures = FailureCollector.collect(payload, _Person, error)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], ValidationFailure)

    def testCollectReturnsATuple(self) -> None:
        """
        Return the collected failures as an immutable tuple.

        Validates the contract consumed by the validation exception.
        """
        error = _conversion_error({}, _Person)
        self.assertIsInstance(FailureCollector.collect({}, _Person, error), tuple)

    def testNestedMappingFailuresAreExpanded(self) -> None:
        """
        Expand a rejected nested mapping into its own field failures.

        Validates the recursion applied to nested schema payloads.
        """
        payload = {"child": {"code": 123}, "count": 1}
        error = _conversion_error(payload, _NestedParent)
        failures = FailureCollector.collect(payload, _NestedParent, error)
        self.assertEqual([f.field for f in failures], ["child.code"])

    def testNestedNonMappingValueIsParsedAsOneFailure(self) -> None:
        """
        Report a single failure when a nested value is not a mapping.

        Validates the fallback of the blame helper.
        """
        payload = {"child": 5, "count": 1}
        error = _conversion_error(payload, _NestedParent)
        failures = FailureCollector.collect(payload, _NestedParent, error)
        self.assertEqual([f.field for f in failures], ["child"])

    def testRulesRunForFieldsThatConverted(self) -> None:
        """
        Run custom rules on values that converted successfully.

        Validates that type errors and rule errors are reported together.
        """
        payload = {"code": "abc", "count": "not-an-int"}
        error = _conversion_error(payload, _RuledParent)
        failures = FailureCollector.collect(payload, _RuledParent, error)
        self.assertEqual({f.field for f in failures}, {"code", "count"})
        self.assertIn("reject", {f.rule for f in failures})

    def testNestedRulesRunWhenASiblingFieldFails(self) -> None:
        """
        Run the rules of a nested schema that converted cleanly.

        Validates that nested rules are reached from the slow path.
        """
        payload = {"child": {"code": "abc"}, "count": "not-an-int"}
        error = _conversion_error(payload, _NestedParent)
        failures = FailureCollector.collect(payload, _NestedParent, error)
        self.assertEqual({f.field for f in failures}, {"child.code", "count"})

class TestFailureCollectorEnforce(TestCase):

    def testUncachedNestedPlanIsBuiltOnDemand(self) -> None:
        """
        Build the nested rule plan when the value type is not cached.

        Validates the cache-miss branch of the rule enforcement pass.
        """
        klass = _uncached_struct("_EnforceColdChild", {"code": [_RejectRule()]})
        failures: list[ValidationFailure] = []
        FailureCollector._enforce(
            [("child", klass(code="abc"), (), klass)], {}, failures,
        )
        self.assertEqual([f.field for f in failures], ["child.code"])

    def testNoneNestedValueIsSkipped(self) -> None:
        """
        Skip nested enforcement when the converted value is None.

        Validates that optional nested schemas never raise on absence.
        """
        failures: list[ValidationFailure] = []
        FailureCollector._enforce([("address", None, (), _Address)], {}, failures)
        self.assertEqual(failures, [])

    def testEmptyNestedPlanProducesNoFailure(self) -> None:
        """
        Produce no failure when the nested schema declares no rule.

        Validates the guard applied before running a nested plan.
        """
        failures: list[ValidationFailure] = []
        FailureCollector._enforce(
            [("address", _Address(zip_code="10001"), (), _Address)], {}, failures,
        )
        self.assertEqual(failures, [])

class TestFailureCollectorBlame(TestCase):

    def testCleanNestedMappingFallsBackToTheParsedError(self) -> None:
        """
        Report the parsed error when the nested mapping blames no field.

        Validates the fallback used when the rejection comes from outside
        the declared fields of the nested schema.
        """
        error = _conversion_error({"zip_code": 1}, _Address)
        failures = FailureCollector._blame(
            error, {"zip_code": "10001"}, _Address, _OptionalNested, "address",
        )
        self.assertEqual([f.field for f in failures], ["address.zip_code"])

class TestFailureCollectorContract(TestCase):

    def testCollectorDeclaresSlots(self) -> None:
        """
        Confirm the collector stores no per-instance state.

        Validates that the class is purely static.
        """
        self.assertEqual(FailureCollector.__slots__, ())
