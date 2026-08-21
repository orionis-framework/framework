from typing import Annotated
import msgspec
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.metadata import Message, Title
from orionis.schemas.rule import Rule
from orionis.schemas.rules_executor import (
    _build_plan,
    _collect_nested,
    _collect_with_plan,
    _PLAN_CACHE,
    _type_contains_nested,
    _warm_child_plan,
)
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

class _AcceptRule(Rule):
    """Rule accepting every value it inspects."""

    __code__ = "accept"
    __message__ = "Accepted."

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        """
        Accept every value.

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
            Always ``True``.
        """
        return True

class _RejectingChild(Schema):
    code: Annotated[str, _RejectRule()]

class _PlainSchema(Schema):
    name: str

class _ParentSchema(Schema):
    child: _RejectingChild
    label: str

class _OptionalParentSchema(Schema):
    child: _RejectingChild | None

class _MessageWithRuleSchema(Schema):
    code: Annotated[str, Message("Code must be a string."), _AcceptRule()]

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
        Freshly created struct class absent from the plan cache.
    """
    klass = msgspec.defstruct(name, [("code", str)])
    klass.__orionis_meta__ = {} if meta is None else meta
    return klass

class TestTypeContainsNested(TestCase):

    def testDirectSchemaIsDetected(self) -> None:
        """
        Detect a bare schema annotation as nested.

        Validates the marker attribute lookup used by the plan builder.
        """
        self.assertTrue(_type_contains_nested(_RejectingChild))

    def testUnionMemberIsDetected(self) -> None:
        """
        Detect a schema declared inside a union annotation.

        Validates that optional nested schemas are still traversed.
        """
        self.assertTrue(_type_contains_nested(_RejectingChild | None))

    def testAnnotatedWrapperIsUnwrapped(self) -> None:
        """
        Detect a schema wrapped in an Annotated alias.

        Validates that metadata never hides the wrapped schema.
        """
        self.assertTrue(_type_contains_nested(Annotated[_RejectingChild, Title("C")]))

    def testPlainAnnotationsAreNotNested(self) -> None:
        """
        Reject annotations carrying no schema at all.

        Validates that scalar and scalar-union fields are skipped.
        """
        self.assertFalse(_type_contains_nested(str))
        self.assertFalse(_type_contains_nested(int | str))

class TestWarmChildPlan(TestCase):

    def testDirectSchemaPlanIsBuilt(self) -> None:
        """
        Build the plan of a nested schema declared directly.

        Validates the eager warm-up performed while building a parent plan.
        """
        klass = _uncached_struct("_WarmDirect")
        self.assertNotIn(klass, _PLAN_CACHE)
        _warm_child_plan(klass)
        self.assertIn(klass, _PLAN_CACHE)

    def testUnionMemberPlanIsBuilt(self) -> None:
        """
        Build the plan of a nested schema declared inside a union.

        Validates that optional nested schemas are warmed up as well.
        """
        klass = _uncached_struct("_WarmUnion")
        self.assertNotIn(klass, _PLAN_CACHE)
        _warm_child_plan(klass | None)
        self.assertIn(klass, _PLAN_CACHE)

    def testCachedPlanIsReused(self) -> None:
        """
        Keep the cached plan when the schema was already warmed up.

        Validates that warming twice never rebuilds the plan.
        """
        cached = _PLAN_CACHE[_RejectingChild]
        _warm_child_plan(_RejectingChild)
        self.assertIs(_PLAN_CACHE[_RejectingChild], cached)

    def testUnrelatedAnnotationIsIgnored(self) -> None:
        """
        Skip annotations that declare no schema.

        Validates that scalar annotations never reach the cache.
        """
        _warm_child_plan(str)
        self.assertNotIn(str, _PLAN_CACHE)

class TestBuildPlan(TestCase):

    def testPlanIsCachedAtClassCreation(self) -> None:
        """
        Cache the validation plan when the schema class is created.

        Validates the pre-build performed by the schema metaclass.
        """
        self.assertIn(_RejectingChild, _PLAN_CACHE)

    def testPlanEntryDescribesTheRuledField(self) -> None:
        """
        Describe name, dotted prefix and validators of a ruled field.

        Validates the shape of the tuple consumed by the hot loop.
        """
        name, dotted, getter, validators, is_nested = _PLAN_CACHE[_RejectingChild][0]
        self.assertEqual(name, "code")
        self.assertEqual(dotted, "code.")
        self.assertEqual(getter(_RejectingChild(code="abc")), "abc")
        self.assertEqual(len(validators), 1)
        self.assertFalse(is_nested)

    def testFieldsWithoutRulesOrNestingAreSkipped(self) -> None:
        """
        Produce an empty plan for a schema declaring no rules.

        Validates that plain schemas cost nothing at validation time.
        """
        self.assertEqual(_PLAN_CACHE[_PlainSchema], ())

    def testNestedFieldIsFlaggedWithoutValidators(self) -> None:
        """
        Flag a nested field for traversal without binding validators.

        Validates that nesting alone keeps the field in the plan.
        """
        entries = {entry[0]: entry for entry in _PLAN_CACHE[_ParentSchema]}
        self.assertIn("child", entries)
        self.assertEqual(entries["child"][3], ())
        self.assertTrue(entries["child"][4])
        self.assertNotIn("label", entries)

    def testValidationMetadataIsNotExecutable(self) -> None:
        """
        Ignore validation metadata while collecting executable rules.

        Validates that only Rule instances become bound validators.
        """
        entry = _PLAN_CACHE[_MessageWithRuleSchema][0]
        self.assertEqual(len(entry[3]), 1)

    def testUnsupportedMetadataRaisesTypeError(self) -> None:
        """
        Reject metadata that is neither a rule nor validation metadata.

        Validates the fail-fast guard applied while building a plan.
        """
        klass = _uncached_struct("_BadMeta", {"code": [object()]})
        with self.assertRaises(TypeError):
            _build_plan(klass)

class TestCollectNested(TestCase):

    def testUncachedChildPlanIsBuiltOnDemand(self) -> None:
        """
        Build the child plan when the nested type is not cached yet.

        Validates the cache-miss branch of the nested traversal.
        """
        klass = _uncached_struct("_NestedColdPlan")
        failures: list[ValidationFailure] = []
        _collect_nested(klass(code="abc"), "child.", failures)
        self.assertIn(klass, _PLAN_CACHE)
        self.assertEqual(failures, [])

    def testChildFailuresAreQualifiedWithThePrefix(self) -> None:
        """
        Prefix nested failures with the dotted path of the parent field.

        Validates the path composition applied to child failures.
        """
        failures: list[ValidationFailure] = []
        _collect_nested(_RejectingChild(code="abc"), "child.", failures)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], ValidationFailure)
        self.assertEqual(failures[0].field, "child.code")

class TestCollectWithPlan(TestCase):

    def testNestedFailuresAreAccumulated(self) -> None:
        """
        Accumulate failures found inside a nested schema.

        Validates that the parent plan drives the nested traversal.
        """
        instance = _ParentSchema(child=_RejectingChild(code="abc"), label="ok")
        failures: list[ValidationFailure] = []
        _collect_with_plan(_PLAN_CACHE[_ParentSchema], instance, "", failures)
        self.assertEqual([f.field for f in failures], ["child.code"])

    def testNoneNestedValueIsSkipped(self) -> None:
        """
        Skip traversal when the nested value is None.

        Validates that optional nested schemas never raise on absence.
        """
        instance = _OptionalParentSchema(child=None)
        failures: list[ValidationFailure] = []
        _collect_with_plan(_PLAN_CACHE[_OptionalParentSchema], instance, "", failures)
        self.assertEqual(failures, [])

    def testEveryFailingRuleIsReported(self) -> None:
        """
        Report every rule failure instead of stopping at the first one.

        Validates the accumulating behaviour of the inner loop.
        """
        instance = _RejectingChild(code="abc")
        failures: list[ValidationFailure] = []
        plan = _PLAN_CACHE[_RejectingChild]
        _collect_with_plan(plan, instance, "", failures)
        _collect_with_plan(plan, instance, "other.", failures)
        self.assertEqual([f.field for f in failures], ["code", "other.code"])
        self.assertEqual({f.rule for f in failures}, {"reject"})
        self.assertEqual({f.message for f in failures}, {"Rejected."})
