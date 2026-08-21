from typing import Annotated
import msgspec
from orionis.schemas.constraints import MaxLength, MinLength
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exception_parser import ValidationErrorParser, _get_fields_map
from orionis.schemas.metadata import Message
from orionis.schemas.schema import Schema
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

class _SimpleSchema(Schema):
    name: str
    age: int

class _NestedChild(Schema):
    code: str

class _ParentSchema(Schema):
    child: _NestedChild
    value: int

class _OptionalParentSchema(Schema):
    child: _NestedChild | None
    value: int

class _LengthSchema(Schema):
    token: Annotated[str, MinLength(5)]

class _TagSchema(Schema):
    tag: Annotated[str, MaxLength(3)]

class _CustomMessageSchema(Schema):
    token: Annotated[
        str,
        MinLength(4, message="Token is too short."),
        Message("Token must be text."),
    ]

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
        Error raised by the conversion.

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

class TestValidationErrorParserParse(TestCase):

    def testTypeErrorReportsTheOffendingField(self) -> None:
        """
        Report the field carried by the msgspec path suffix.

        Validates that the dotted path is stripped into a field name.
        """
        error = _conversion_error({"name": "Alice", "age": "x"}, _SimpleSchema)
        failure = ValidationErrorParser.parse(error, _SimpleSchema)
        self.assertIsInstance(failure, ValidationFailure)
        self.assertEqual(failure.field, "age")
        self.assertEqual(failure.rule, "type")

    def testMissingRequiredFieldIsReported(self) -> None:
        """
        Report a missing required field with the ``missing`` rule.

        Validates the branch reading the field name from the message.
        """
        error = _conversion_error({}, _SimpleSchema)
        failure = ValidationErrorParser.parse(error, _SimpleSchema)
        self.assertEqual(failure.field, "name")
        self.assertEqual(failure.rule, "missing")

    def testNestedFieldPathIsPreserved(self) -> None:
        """
        Preserve the dotted path of a nested field.

        Validates that nested errors are attributed to the leaf field.
        """
        error = _conversion_error({"child": {"code": 9}, "value": 1}, _ParentSchema)
        failure = ValidationErrorParser.parse(error, _ParentSchema)
        self.assertEqual(failure.field, "child.code")

    def testParseWorksWithoutASchema(self) -> None:
        """
        Parse an error when no schema is supplied.

        Validates that custom message resolution is skipped gracefully.
        """
        error = _conversion_error({"name": 1, "age": 30}, _SimpleSchema)
        failure = ValidationErrorParser.parse(error)
        self.assertEqual(failure.field, "name")
        self.assertIsInstance(failure.message, str)

    def testMinLengthConstraintIsIdentified(self) -> None:
        """
        Identify the ``min_length`` rule from the msgspec message.

        Validates the constraint detection for short strings.
        """
        error = _conversion_error({"token": "ab"}, _LengthSchema)
        failure = ValidationErrorParser.parse(error, _LengthSchema)
        self.assertEqual(failure.rule, "min_length")

    def testMaxLengthConstraintIsIdentified(self) -> None:
        """
        Identify the ``max_length`` rule from the msgspec message.

        Validates the constraint detection for long strings.
        """
        error = _conversion_error({"tag": "toolong"}, _TagSchema)
        failure = ValidationErrorParser.parse(error, _TagSchema)
        self.assertEqual(failure.rule, "max_length")

    def testCustomConstraintMessageReplacesTheDefault(self) -> None:
        """
        Replace the msgspec message with the declared custom message.

        Validates the constraint message lookup performed on the schema.
        """
        error = _conversion_error({"token": "ab"}, _CustomMessageSchema)
        failure = ValidationErrorParser.parse(error, _CustomMessageSchema)
        self.assertEqual(failure.message, "Token is too short.")

class TestValidationErrorParserParseAt(TestCase):

    def testFieldPathIsPrefixedWithTheBase(self) -> None:
        """
        Prefix the reported field with the path of the converted value.

        Validates the sub-conversion entry point used by the collector.
        """
        error = _conversion_error({"code": 9}, _NestedChild)
        failure = ValidationErrorParser.parseAt(error, _ParentSchema, "child")
        self.assertEqual(failure.field, "child.code")

    def testMissingFieldPathIsPrefixedWithTheBase(self) -> None:
        """
        Prefix a missing nested field with the path of its parent.

        Validates the missing-field branch of the sub-conversion parser.
        """
        error = _conversion_error({}, _NestedChild)
        failure = ValidationErrorParser.parseAt(error, _ParentSchema, "child")
        self.assertEqual(failure.field, "child.code")
        self.assertEqual(failure.rule, "missing")

    def testValueWithoutPathKeepsTheBaseAsField(self) -> None:
        """
        Attribute a path-less error to the converted value itself.

        Validates the branch used when msgspec reports no path suffix.
        """
        error = _conversion_error(5, _NestedChild)
        failure = ValidationErrorParser.parseAt(error, _ParentSchema, "child")
        self.assertEqual(failure.field, "child")

class TestValidationErrorParserJoinPath(TestCase):

    def testRelativePathIsReturnedWithoutABase(self) -> None:
        """
        Return the relative path when no base is supplied.

        Validates the root-level branch of the path builder.
        """
        self.assertEqual(ValidationErrorParser._joinPath("", "code"), "code")

    def testBaseIsReturnedWithoutARelativePath(self) -> None:
        """
        Return the base path when no relative path is supplied.

        Validates the branch used for errors on the value itself.
        """
        self.assertEqual(ValidationErrorParser._joinPath("child", ""), "child")

    def testSequenceIndexIsAppendedWithoutASeparator(self) -> None:
        """
        Append a sequence index directly to the base path.

        Validates that indices never receive a leading dot.
        """
        self.assertEqual(ValidationErrorParser._joinPath("tags", "[0]"), "tags[0]")

    def testNestedFieldsAreJoinedWithADot(self) -> None:
        """
        Join a base path and a field name with a dot.

        Validates the default composition of dotted paths.
        """
        joined = ValidationErrorParser._joinPath("child", "code")
        self.assertEqual(joined, "child.code")

class TestValidationErrorParserCustomMessage(TestCase):

    def testDeclaredMessageIsReturned(self) -> None:
        """
        Return the message declared for the violated constraint.

        Validates the lookup keyed by the detected constraint.
        """
        raw = "Expected `str` of length >= 4"
        result = ValidationErrorParser._customMessage(
            _CustomMessageSchema, "token", raw,
        )
        self.assertEqual(result, "Token is too short.")

    def testUnknownConstraintReturnsNone(self) -> None:
        """
        Return None when the raw message matches no known constraint.

        Validates the guard applied before the message lookup.
        """
        result = ValidationErrorParser._customMessage(
            _CustomMessageSchema, "token", "an entirely unrelated failure",
        )
        self.assertIsNone(result)

    def testFieldWithoutMessagesReturnsNone(self) -> None:
        """
        Return None for a field declaring no custom message.

        Validates the early exit of the message resolver.
        """
        raw = "Expected `str` of length >= 4"
        self.assertIsNone(
            ValidationErrorParser._customMessage(_SimpleSchema, "name", raw),
        )

class TestValidationErrorParserSchemaResolution(TestCase):

    def testPlainFieldResolvesToTheRootSchema(self) -> None:
        """
        Resolve a dot-less path against the root schema.

        Validates the fast path of the schema traversal.
        """
        self.assertEqual(
            ValidationErrorParser._resolveSchema(_ParentSchema, "value"),
            (_ParentSchema, "value"),
        )

    def testNestedPathResolvesToTheChildSchema(self) -> None:
        """
        Resolve a dotted path to the schema owning the leaf field.

        Validates the traversal used to find custom messages.
        """
        self.assertEqual(
            ValidationErrorParser._resolveSchema(_ParentSchema, "child.code"),
            (_NestedChild, "code"),
        )

    def testUnresolvablePathFallsBackToTheRootSchema(self) -> None:
        """
        Fall back to the root schema when a path segment is not nested.

        Validates the guard protecting the traversal from bad paths.
        """
        self.assertEqual(
            ValidationErrorParser._resolveSchema(_ParentSchema, "value.deep"),
            (_ParentSchema, "value.deep"),
        )

    def testOptionalNestedTypeIsResolved(self) -> None:
        """
        Resolve a nested schema declared inside a union annotation.

        Validates support for optional nested schemas.
        """
        resolved = ValidationErrorParser._resolveNestedType(
            _OptionalParentSchema, "child",
        )
        self.assertIs(resolved, _NestedChild)

    def testResolvedNestedTypeIsCached(self) -> None:
        """
        Return the cached nested type on repeated look-ups.

        Validates the cache guarding the error path.
        """
        first = ValidationErrorParser._resolveNestedType(_ParentSchema, "child")
        second = ValidationErrorParser._resolveNestedType(_ParentSchema, "child")
        self.assertIs(first, second)

    def testUnknownFieldResolvesToNone(self) -> None:
        """
        Return None when the schema declares no such field.

        Validates the fallback for paths that do not exist.
        """
        self.assertIsNone(
            ValidationErrorParser._resolveNestedType(_ParentSchema, "absent"),
        )

class TestValidationErrorParserConstraintKeys(TestCase):

    def testUnknownMessageReturnsNone(self) -> None:
        """
        Return None when the message matches no registered pattern.

        Validates the fallback that classifies an error as a type error.
        """
        self.assertIsNone(
            ValidationErrorParser._matchConstraintKey("unrecognised failure text"),
        )

    def testGreaterThanIsDetected(self) -> None:
        """
        Detect the ``gt`` constraint from the message.

        Validates the ordered pattern scan for exclusive lower bounds.
        """
        self.assertEqual(
            ValidationErrorParser._matchConstraintKey("Expected `int` x > 0"),
            "gt",
        )

    def testLessThanIsDetected(self) -> None:
        """
        Detect the ``lt`` constraint from the message.

        Validates the ordered pattern scan for exclusive upper bounds.
        """
        self.assertEqual(
            ValidationErrorParser._matchConstraintKey("Expected `int` x < 100"),
            "lt",
        )

class TestFieldsMapCache(TestCase):

    def testFieldsMapIsCachedPerSchema(self) -> None:
        """
        Return the very same mapping object on repeated calls.

        Validates the cache that avoids re-inspecting struct fields.
        """
        self.assertIs(_get_fields_map(_TagSchema), _get_fields_map(_TagSchema))

    def testFieldsMapExposesDeclaredFields(self) -> None:
        """
        Expose every declared field of the inspected schema.

        Validates the mapping consumed by the nested type resolver.
        """
        self.assertEqual(set(_get_fields_map(_ParentSchema)), {"child", "value"})

class TestValidationErrorParserContract(TestCase):

    def testParserDeclaresSlots(self) -> None:
        """
        Confirm the parser stores no per-instance state.

        Validates that the class is purely static.
        """
        self.assertEqual(ValidationErrorParser.__slots__, ())
