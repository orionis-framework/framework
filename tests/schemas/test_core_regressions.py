# ruff: noqa: PT009, PT027, S102, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Compile one fixed source fixture to exercise Python's future-annotation mode.
"""Exercise schema compilation, nested validation and bounded metadata ownership."""

import gc
import weakref
from typing import Annotated, get_type_hints

import msgspec

from orionis.schemas import Schema
from orionis.schemas.coercion import _coerce_mapping, coerce_payload
from orionis.schemas.compiler import MetaCompiler
from orionis.schemas.constraint_plan import constraint_plan, register_messages
from orionis.schemas.constraints import GreaterThan
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.instance_payload import instance_payload
from orionis.schemas.schema import SchemaMeta
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase


class _PositiveChild(Schema):
    """Declare a native constraint that constructors do not enforce."""

    amount: Field[int, GreaterThan(0)]


class _NestedInput(Schema):
    """Keep schema instances inside native payload containers."""

    children: dict[str, list[_PositiveChild]]


class _TaggedChild(Schema, tag="child"):
    """Select constrained instances through a tagged union."""

    amount: Field[int, GreaterThan(0)]


class _OtherChild(Schema, tag="other"):
    """Provide a distinct valid alternative for union selection."""

    label: str


class _UnionInput(Schema):
    """Retain a child's declared constraint while selecting its union branch."""

    child: _TaggedChild | _OtherChild


class _ArrayChild(Schema, array_like=True, tag="row"):
    """Expose a positional child that still needs structural revalidation."""

    amount: Field[int, GreaterThan(0)]


class _ArrayInput(Schema):
    """Keep array-like instances inside an ordinary mapping payload."""

    child: _ArrayChild


class _UntypedInput(Schema):
    """Preserve unconstrained object values without interpreting their contents."""

    value: object


class TestSchemaCoreRegressions(TestCase):
    """Protect validation boundaries and release discarded dynamic declarations."""

    async def testNativePayloadContainersRevalidateExistingChildren(self) -> None:
        """Reject mutated child instances even when the root is an input mapping."""
        child = _PositiveChild(2)
        child.amount = -1
        for payload, schema, field in (
            (
                {"children": {"primary": [child]}},
                _NestedInput,
                "children['primary'][0].amount",
            ),
            ({"child": _TaggedChild(-1)}, _UnionInput, "child.amount"),
            ({"child": _ArrayChild(-1)}, _ArrayInput, "child.amount"),
        ):
            with self.subTest(schema=schema.__name__):
                original_child = payload.get("child", child)
                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate(payload, schema)
                self.assertIn(field, caught.exception.errors)
                if "child" in payload:
                    self.assertIs(payload["child"], original_child)
                else:
                    self.assertIs(payload["children"]["primary"][0], child)
        self.assertEqual(child.amount, -1)
        untyped = await Validator.validate({"value": child}, _UntypedInput)
        self.assertIs(untyped.value, child)
        raw_child = {"amount": 2}
        native_payload = {"children": {"primary": [raw_child]}}
        self.assertIs(coerce_payload(native_payload, _NestedInput), native_payload)
        mixed_payload = {"children": {"primary": [raw_child, child]}}
        prepared = coerce_payload(mixed_payload, _NestedInput)
        self.assertIsNot(prepared, mixed_payload)
        self.assertIs(prepared["children"]["primary"][0], raw_child)
        self.assertEqual(prepared["children"]["primary"][1], {"amount": -1})
        self.assertIs(mixed_payload["children"]["primary"][1], child)
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate(mixed_payload, _NestedInput)
        self.assertIn("children['primary'][1].amount", caught.exception.errors)
        child.amount = 3
        validated = await Validator.validate(mixed_payload, _NestedInput)
        self.assertEqual(
            [item.amount for item in validated.children["primary"]],
            [2, 3],
        )

    async def testExplicitAnnotationNamespacesCompileConstraints(self) -> None:
        """Apply native constraints to classes created from explicit annotations."""
        schema = SchemaMeta(
            "ExplicitConstraintSchema",
            (Schema,),
            {
                "__module__": __name__,
                "__annotations__": {"amount": Field[int, GreaterThan(0)]},
            },
        )
        self.assertEqual((await Validator.validate({"amount": 2}, schema)).amount, 2)
        with self.assertRaises(ValidationException):
            await Validator.validate({"amount": 0}, schema)

    async def testFutureAnnotationModeCompilesConstraints(self) -> None:
        """Apply constraints when a Python 3.14 module requests string annotations."""
        namespace = {"__name__": __name__, "Schema": Schema}
        source = (
            "from __future__ import annotations\n"
            "class FutureConstraintSchema(Schema):\n"
            "    amount: Field[int, GreaterThan(0)]\n"
        )
        exec(
            compile(source, "<schema-future-fixture>", "exec", dont_inherit=True),
            namespace,
        )
        schema = namespace["FutureConstraintSchema"]
        self.assertEqual((await Validator.validate({"amount": 2}, schema)).amount, 2)
        with self.assertRaises(ValidationException):
            await Validator.validate({"amount": 0}, schema)

    def testCoreAnnotationsResolveAtRuntime(self) -> None:
        """Resolve runtime-facing metadata and validation signatures completely."""
        for function in (
            SchemaMeta._wrap,
            MetaCompiler.compile,
            Validator.validate,
            _coerce_mapping,
        ):
            with self.subTest(function=function.__qualname__):
                self.assertIn("return", get_type_hints(function))

    def testInstancePlansReleaseDiscardedStructClasses(self) -> None:
        """Release temporary struct types after their instances are expanded."""
        references = []
        for index in range(40):
            schema = msgspec.defstruct(f"TemporaryPayload{index}", [("amount", int)])
            self.assertEqual(instance_payload(schema(index)), {"amount": index})
            references.append(weakref.ref(schema))
        del schema
        gc.collect()
        self.assertFalse(any(reference() is not None for reference in references))

    def testConstraintPlansBoundDiscardedAnnotationRetention(self) -> None:
        """Bound metadata retention after more declarations than cache capacity."""
        references = []
        for index in range(1100):
            # Keep sampled aliases distinct from live declarations in other tests.
            annotation = Annotated[int, msgspec.Meta(ge=index), object()]
            constraint_plan(annotation)
            references.append(weakref.ref(annotation))
        del annotation
        gc.collect()
        self.assertLessEqual(
            sum(reference() is not None for reference in references),
            1024,
        )

    def testLocalMessagesDoNotRetainDiscardedAnnotationsGlobally(self) -> None:
        """Keep messages with their annotations without an unbounded registry."""
        references = []
        for index in range(1100):
            annotation = register_messages(int, {"type": f"Message {index}"})
            references.append(weakref.ref(annotation))
        del annotation
        gc.collect()
        # The standard typing implementation retains at most 128 recent aliases.
        self.assertLessEqual(
            sum(reference() is not None for reference in references),
            128,
        )
