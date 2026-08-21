import msgspec
from orionis.schemas.compiler import MetaCompiler, MetadataConflictError
from orionis.schemas.constraints import (
    GreaterThan,
    GreaterThanOrEqual,
    LessThan,
    LessThanOrEqual,
    MaxLength,
    MinLength,
    MultipleOf,
    Pattern,
    TimezoneAware,
    TimezoneNaive,
)
from orionis.schemas.metadata import (
    Description,
    Examples,
    Extra,
    ExtraJsonSchema,
    Title,
)
from orionis.test import TestCase

class TestMetaCompilerCompile(TestCase):

    def testCompileEmptyListReturnsDefaultMeta(self) -> None:
        """
        Compile an empty metadata list and return a default msgspec.Meta.

        Validates that calling compile with an empty list succeeds and
        returns a msgspec.Meta instance.
        """
        result = MetaCompiler.compile([])
        self.assertIsInstance(result, msgspec.Meta)

    def testCompileGreaterThanSetsMeta(self) -> None:
        """
        Compile GreaterThan and verify the resulting Meta gt attribute.

        Validates that the gt field of the returned Meta matches the
        GreaterThan constraint value.
        """
        result = MetaCompiler.compile([GreaterThan(5)])
        self.assertEqual(result.gt, 5)

    def testCompileGreaterThanOrEqualSetsMeta(self) -> None:
        """
        Compile GreaterThanOrEqual and verify the resulting Meta ge attribute.

        Validates that the ge field of the returned Meta matches the
        GreaterThanOrEqual constraint value.
        """
        result = MetaCompiler.compile([GreaterThanOrEqual(0)])
        self.assertEqual(result.ge, 0)

    def testCompileLessThanSetsMeta(self) -> None:
        """
        Compile LessThan and verify the resulting Meta lt attribute.

        Validates that the lt field of the returned Meta matches the
        LessThan constraint value.
        """
        result = MetaCompiler.compile([LessThan(100)])
        self.assertEqual(result.lt, 100)

    def testCompileLessThanOrEqualSetsMeta(self) -> None:
        """
        Compile LessThanOrEqual and verify the resulting Meta le attribute.

        Validates that the le field of the returned Meta matches the
        LessThanOrEqual constraint value.
        """
        result = MetaCompiler.compile([LessThanOrEqual(99)])
        self.assertEqual(result.le, 99)

    def testCompileMultipleOfSetsMeta(self) -> None:
        """
        Compile MultipleOf and verify the resulting Meta multiple_of attribute.

        Validates that the multiple_of field of the returned Meta matches the
        MultipleOf constraint value.
        """
        result = MetaCompiler.compile([MultipleOf(3)])
        self.assertEqual(result.multiple_of, 3)

    def testCompilePatternSetsMeta(self) -> None:
        """
        Compile Pattern and verify the resulting Meta pattern attribute.

        Validates that the pattern field of the returned Meta matches the
        Pattern constraint regex string.
        """
        result = MetaCompiler.compile([Pattern(r"^\d+$")])
        self.assertEqual(result.pattern, r"^\d+$")

    def testCompileMinLengthSetsMeta(self) -> None:
        """
        Compile MinLength and verify the resulting Meta min_length attribute.

        Validates that the min_length field of the returned Meta matches the
        MinLength constraint value.
        """
        result = MetaCompiler.compile([MinLength(2)])
        self.assertEqual(result.min_length, 2)

    def testCompileMaxLengthSetsMeta(self) -> None:
        """
        Compile MaxLength and verify the resulting Meta max_length attribute.

        Validates that the max_length field of the returned Meta matches the
        MaxLength constraint value.
        """
        result = MetaCompiler.compile([MaxLength(50)])
        self.assertEqual(result.max_length, 50)

    def testCompileTimezoneAwareSetsMetaTzTrue(self) -> None:
        """
        Compile TimezoneAware and verify the resulting Meta tz attribute.

        Validates that the tz field of the returned Meta is True when
        TimezoneAware is included.
        """
        result = MetaCompiler.compile([TimezoneAware()])
        self.assertTrue(result.tz)

    def testCompileTimezoneNaiveSetsMetaTzFalse(self) -> None:
        """
        Compile TimezoneNaive and verify the resulting Meta tz attribute.

        Validates that the tz field of the returned Meta is False when
        TimezoneNaive is included.
        """
        result = MetaCompiler.compile([TimezoneNaive()])
        self.assertFalse(result.tz)

    def testCompileTitleSetsMeta(self) -> None:
        """
        Compile Title metadata and verify the resulting Meta title attribute.

        Validates that the title field of the returned Meta matches the
        Title value string.
        """
        result = MetaCompiler.compile([Title("My Field")])
        self.assertEqual(result.title, "My Field")

    def testCompileDescriptionSetsMeta(self) -> None:
        """
        Compile Description metadata and verify the resulting Meta attribute.

        Validates that the description field of the returned Meta matches the
        Description value string.
        """
        result = MetaCompiler.compile([Description("A description.")])
        self.assertEqual(result.description, "A description.")

    def testCompileExamplesSetsMeta(self) -> None:
        """
        Compile Examples metadata and verify the resulting Meta examples list.

        Validates that the examples field of the returned Meta is a list
        matching the Examples values list.
        """
        result = MetaCompiler.compile([Examples([1, "two", 3.0])])
        self.assertEqual(result.examples, [1, "two", 3.0])

    def testCompileExtraJsonSchemaSetsMeta(self) -> None:
        """
        Compile ExtraJsonSchema metadata and verify the resulting Meta.

        Validates that the extra_json_schema field of the returned Meta
        matches the ExtraJsonSchema data dict.
        """
        result = MetaCompiler.compile([ExtraJsonSchema({"readOnly": True})])
        self.assertEqual(result.extra_json_schema, {"readOnly": True})

    def testCompileExtraSetsMeta(self) -> None:
        """
        Compile Extra metadata and verify the resulting Meta extra attribute.

        Validates that the extra field of the returned Meta matches the
        Extra data dict.
        """
        result = MetaCompiler.compile([Extra({"key": "value"})])
        self.assertEqual(result.extra, {"key": "value"})

    def testCompileMultipleConstraintsTogether(self) -> None:
        """
        Compile multiple non-conflicting constraints in one call.

        Validates that all constraints are applied simultaneously and
        each corresponding Meta attribute is set correctly.
        """
        result = MetaCompiler.compile(
            [GreaterThanOrEqual(0), LessThanOrEqual(100), MultipleOf(5)],
        )
        self.assertEqual(result.ge, 0)
        self.assertEqual(result.le, 100)
        self.assertEqual(result.multiple_of, 5)

class TestMetaCompilerConflicts(TestCase):

    def testDuplicateConstraintRaises(self) -> None:
        """
        Raise MetadataConflictError when the same constraint type appears twice.

        Validates that _index detects duplicate metadata types and raises
        MetadataConflictError with a descriptive message.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([MinLength(2), MinLength(5)])

    def testGreaterThanAndGreaterThanOrEqualRaises(self) -> None:
        """
        Raise MetadataConflictError for ambiguous lower bound combination.

        Validates that combining GreaterThan and GreaterThanOrEqual on
        the same field is rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([GreaterThan(5), GreaterThanOrEqual(5)])

    def testLessThanAndLessThanOrEqualRaises(self) -> None:
        """
        Raise MetadataConflictError for ambiguous upper bound combination.

        Validates that combining LessThan and LessThanOrEqual on the same
        field is rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([LessThan(10), LessThanOrEqual(10)])

    def testImpossibleNumericRangeRaises(self) -> None:
        """
        Raise MetadataConflictError for an empty numeric range.

        Validates that GreaterThan(10) combined with LessThan(5) is
        detected as an impossible range and rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([GreaterThan(10), LessThan(5)])

    def testImpossibleLengthRangeRaises(self) -> None:
        """
        Raise MetadataConflictError when MinLength exceeds MaxLength.

        Validates that MinLength(100) combined with MaxLength(10) is
        detected as an impossible length range and rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([MinLength(100), MaxLength(10)])

    def testTimezoneAwareAndTimezoneNaiveRaises(self) -> None:
        """
        Raise MetadataConflictError for conflicting timezone constraints.

        Validates that combining TimezoneAware and TimezoneNaive on the
        same field is detected and rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([TimezoneAware(), TimezoneNaive()])

    def testMixedBoundsWithEqualValuesRaise(self) -> None:
        """
        Raise MetadataConflictError when mixed bounds share the same value.

        Validates that an inclusive lower bound combined with an exclusive
        upper bound of the same value leaves no valid value.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([GreaterThanOrEqual(10), LessThan(10)])

    def testEqualInclusiveBoundsAreAllowed(self) -> None:
        """
        Allow equal inclusive bounds as a valid degenerate range.

        Validates that GreaterThanOrEqual(5) combined with LessThanOrEqual(5)
        is accepted (the only valid value is exactly 5).
        """
        result = MetaCompiler.compile(
            [GreaterThanOrEqual(5), LessThanOrEqual(5)],
        )
        self.assertEqual(result.ge, 5)
        self.assertEqual(result.le, 5)

class TestMetaCompilerInvalidValues(TestCase):

    def testMultipleOfZeroRaises(self) -> None:
        """
        Raise MetadataConflictError when MultipleOf value is zero.

        Validates that a zero divisor in MultipleOf is detected as an
        invalid value and rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([MultipleOf(0)])

    def testMultipleOfNegativeRaises(self) -> None:
        """
        Raise MetadataConflictError when MultipleOf value is negative.

        Validates that a negative divisor in MultipleOf is rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([MultipleOf(-2)])

    def testMinLengthNegativeRaises(self) -> None:
        """
        Raise MetadataConflictError when MinLength value is negative.

        Validates that a negative minimum length is detected as invalid
        and rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([MinLength(-1)])

    def testMaxLengthNegativeRaises(self) -> None:
        """
        Raise MetadataConflictError when MaxLength value is negative.

        Validates that a negative maximum length is detected as invalid
        and rejected.
        """
        with self.assertRaises(MetadataConflictError):
            MetaCompiler.compile([MaxLength(-1)])

class TestMetaCompilerContract(TestCase):

    def testCompilerDeclaresSlots(self) -> None:
        """
        Confirm the compiler stores no per-instance state.

        Validates that the class is purely static.
        """
        self.assertEqual(MetaCompiler.__slots__, ())

    def testMetadataConflictErrorIsValueError(self) -> None:
        """
        Confirm MetadataConflictError inherits from ValueError.

        Validates that the exception hierarchy allows catching it
        via the built-in ValueError.
        """
        self.assertTrue(issubclass(MetadataConflictError, ValueError))
