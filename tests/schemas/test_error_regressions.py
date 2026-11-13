# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve public error contracts and native validation paths."""

from collections import UserList
import gc
from typing import Annotated, get_type_hints
from unittest.mock import patch
from weakref import ref

import msgspec

from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exception_parser import ValidationErrorParser, _get_fields_map
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.failure_collector import _field_plan
from orionis.schemas import rules_executor
from orionis.schemas.metadata import Message
from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase


class _RequiredLeaf(msgspec.Struct):
    """Require an integer at a nested native field."""

    code: int


class _RequiredBranch(msgspec.Struct):
    """Keep a nested required field in the native error path."""

    child: _RequiredLeaf


class _PunctuationField(msgspec.Struct, rename={"value": "..."}):
    """Use a valid encoded name that contains only path punctuation."""

    value: int


class _TaggedFirst(Schema, tag="first"):
    """Provide a type message that belongs only to the first union branch."""

    value: Annotated[int, Message("First branch requires an integer.")]


class _TaggedSecond(Schema, tag="second"):
    """Provide a separate type message for the other union branch."""

    value: Annotated[int, Message("Second branch requires an integer.")]


class _AmbiguousParent(Schema):
    """Expose a tagged union whose error path alone cannot select a branch."""

    child: _TaggedFirst | _TaggedSecond


def _cached_nested_types() -> tuple:
    """Return weak references after populating real parser caches for local types."""
    leaf = msgspec.defstruct("_TransientLeaf", [("value", int)])
    leaf.__orionis_constraints__ = {}
    parent = msgspec.defstruct("_TransientParent", [("child", leaf)])
    ValidationErrorParser._resolveNestedType(parent, "child")
    return ref(parent), ref(leaf)


def _cached_recursive_type() -> tuple:
    """Return a weak reference after caching a field that refers to its own type."""

    class Recursive(msgspec.Struct):
        """Retain a legitimate self-referential field annotation."""

        child: Recursive | None = None

    _get_fields_map(Recursive)
    return (ref(Recursive),)


class TestErrorRegressions(TestCase):
    """Exercise real failure construction and msgspec conversion diagnostics."""

    def testFailureCollectionAcceptsTheDeclaredSequenceContract(self) -> None:
        """Collect an arbitrary sequence while preserving failure identity and order."""
        first = ValidationFailure("name", "type", "Invalid name.")
        second = ValidationFailure("name", "custom", "Rejected name.")
        exception = ValidationException(UserList([first, second]))
        self.assertEqual(exception.failures, (first, second))
        self.assertIs(exception.failure, first)
        self.assertEqual(
            exception.errors["name"],
            [
                {"rule": "type", "message": "Invalid name."},
                {"rule": "custom", "message": "Rejected name."},
            ],
        )

    def testExplicitEmptySummaryDoesNotReplaceFieldErrors(self) -> None:
        """Keep an explicitly empty summary independently of its field details."""
        failure = ValidationFailure("name", "type", "Invalid name.")
        exception = ValidationException(failure, message="")
        self.assertEqual(str(exception), "")
        self.assertEqual(
            exception.error(),
            {
                "message": "",
                "errors": {"name": [{"rule": "type", "message": "Invalid name."}]},
            },
        )

    def testExceptionConstructorAnnotationsResolve(self) -> None:
        """Resolve the declared failure collection without caller namespaces."""
        annotations = get_type_hints(ValidationException.__init__)
        self.assertIn("failures", annotations)
        self.assertIs(annotations["return"], type(None))

    def testNativeNestedMissingFieldKeepsItsLeafAndRule(self) -> None:
        """Append the missing leaf to the actual native parent path."""
        with self.assertRaises(msgspec.ValidationError) as raised:
            msgspec.convert({"child": {}}, type=_RequiredBranch)
        failure = ValidationErrorParser.parse(raised.exception, _RequiredBranch)
        self.assertEqual(failure.field, "child.code")
        self.assertEqual(failure.rule, "missing")

    def testQuotedTextDoesNotChangeTheNativeFailureKind(self) -> None:
        """Classify the native constraint instead of phrases inside its pattern."""
        for pattern in ("missing required field `code`", "of length >="):
            with self.subTest(pattern=pattern):
                annotation = Annotated[str, msgspec.Meta(pattern=pattern)]
                with self.assertRaises(msgspec.ValidationError) as raised:
                    msgspec.convert("", type=annotation)
                failure = ValidationErrorParser.parseAt(raised.exception, None, "value")
                self.assertEqual(failure.field, "value")
                self.assertEqual(failure.rule, "pattern")
                self.assertEqual(failure.message, str(raised.exception))
        schema = msgspec.defstruct(
            "_RejectUnknown",
            [("value", int)],
            forbid_unknown_fields=True,
        )
        with self.assertRaises(msgspec.ValidationError) as raised:
            msgspec.convert({"value": 1, "of length >=": 2}, type=schema)
        failure = ValidationErrorParser.parse(raised.exception, schema)
        self.assertEqual(failure.rule, "type")
        self.assertEqual(failure.message, str(raised.exception))

    def testEncodedPunctuationFieldKeepsItsOriginalName(self) -> None:
        """Parse a native error for a valid encoded field without losing its name."""
        with self.assertRaises(msgspec.ValidationError) as raised:
            msgspec.convert({"...": "invalid"}, type=_PunctuationField)
        failure = ValidationErrorParser.parse(raised.exception, _PunctuationField)
        self.assertEqual(failure.field, "...")
        self.assertEqual(failure.rule, "type")

    async def testAmbiguousUnionPathDoesNotBorrowAnotherBranchesMessage(self) -> None:
        """Preserve the native diagnostic when its path cannot identify a union tag."""
        with self.assertRaises(msgspec.ValidationError) as raised:
            msgspec.convert(
                {"child": {"type": "second", "value": "invalid"}},
                type=_AmbiguousParent,
            )
        failure = ValidationErrorParser.parse(raised.exception, _AmbiguousParent)
        self.assertEqual(failure.field, "child.value")
        self.assertEqual(failure.rule, "type")
        self.assertEqual(failure.message, "Expected `int`, got `str`")
        with self.assertRaises(ValidationException) as collected:
            await Validator.validate(
                {"child": {"type": "second", "value": "invalid"}},
                _AmbiguousParent,
            )
        self.assertEqual(
            collected.exception.errors["child.value"],
            [
                {"rule": "type", "message": "Second branch requires an integer."},
            ],
        )

    def testParserCachesReleaseNestedAndRecursiveTypes(self) -> None:
        """Release dynamic classes even when cached field types refer to themselves."""
        for factory in (_cached_nested_types, _cached_recursive_type):
            with self.subTest(factory=factory.__name__):
                references = factory()
                gc.collect()
                for reference in references:
                    self.assertIsNone(reference())

    def testCollectorPlansDoNotRetainEvictedSchemaClasses(self) -> None:
        """Release collector metadata after the bounded rule cache evicts its owner."""
        with (
            patch.dict(rules_executor._PLAN_CACHE, clear=True),
            patch.object(rules_executor, "_PLAN_CACHE_MAX", 8),
        ):

            class Parent(msgspec.Struct):
                """Provide a cached parent field before inspecting its subclass."""

                value: int

            class Child(Parent):
                """Extend the parent's fields without inheriting its cached plan."""

                other: str

            _get_fields_map(Parent)
            _field_plan(Parent)
            self.assertEqual(set(_get_fields_map(Child)), {"value", "other"})
            self.assertEqual(
                [entry[0] for entry in _field_plan(Child)],
                ["value", "other"],
            )
            first = msgspec.defstruct("_TransientCollected", [("value", int)])
            reference = ref(first)
            _field_plan(first)
            del first
            for index in range(8):
                schema = msgspec.defstruct(f"_EvictCollector{index}", [("value", int)])
                rules_executor._build_plan(schema)
            del schema
            gc.collect()
            self.assertIsNone(reference())
