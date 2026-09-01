import base64
from pathlib import Path
from orionis.environment.dynamic.caster import EnvironmentCaster
from orionis.environment.enums.value_type import EnvironmentValueType
from orionis.test import TestCase

# Truthy and falsy spellings accepted by the boolean parser.
_TRUE_WORDS: tuple[str, ...] = ("true", "1", "yes", "on", "enabled")
_FALSE_WORDS: tuple[str, ...] = ("false", "0", "no", "off", "disabled")

# Bytes that cannot be decoded as UTF-8.
_NON_UTF8: bytes = b"\xff\xfe"

# Lone surrogate that cannot be encoded as UTF-8 either.
_LONE_SURROGATE: str = "\ud800"

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _ExtendedCaster(EnvironmentCaster):
    """Caster advertising a type hint that has no dispatch branch."""

    OPTIONS = frozenset({*EnvironmentCaster.OPTIONS, "unknown"})

class _UncoercibleValue:
    """Value that cannot be coerced to a boolean."""

    __slots__ = ()

    def __bool__(self) -> bool:
        """Refuse the truthiness protocol."""
        error_msg = "truthiness is undefined"
        raise ValueError(error_msg)

    def __repr__(self) -> str:
        """Return a stable, printable representation."""
        return "<uncoercible>"

class _UnprintableOnceValue:
    """Value whose first string conversion fails and then recovers."""

    __slots__ = ("conversions",)

    def __init__(self) -> None:
        self.conversions: int = 0

    def __str__(self) -> str:
        """Fail the first conversion so the error path can be reached."""
        self.conversions += 1
        if self.conversions == 1:
            error_msg = "value is not printable"
            raise ValueError(error_msg)
        return "recovered"

def build_caster(type_hint: str, value: object) -> EnvironmentCaster:
    """
    Build a caster holding an arbitrary value under a given type hint.

    The public constructor can only attach a type hint to a string, so this
    helper is required to exercise the defensive branches that guard against
    values injected by other means.

    Parameters
    ----------
    type_hint : str
        Canonical type hint to attach to the caster.
    value : object
        Raw value the caster must operate on.

    Returns
    -------
    EnvironmentCaster
        Caster carrying the requested hint and raw value.
    """
    caster = EnvironmentCaster(f"{type_hint}:seed")
    caster._EnvironmentCaster__value_raw = value
    return caster

# ---------------------------------------------------------------------------
# TestEnvironmentCasterSupportedTypes
# ---------------------------------------------------------------------------

class TestEnvironmentCasterSupportedTypes(TestCase):

    def testExposesEveryEnumeratedTypeAsAnOption(self) -> None:
        """
        Expose every enumerated value type as a supported option.

        Validates that the fast membership set never drifts from the
        enumeration that documents the ``"<type>:<value>"`` convention.
        """
        expected = frozenset(member.value for member in EnvironmentValueType)
        self.assertEqual(EnvironmentCaster.supportedTypes(), expected)

    def testExposesTheOptionsAsAnImmutableSet(self) -> None:
        """
        Expose the options as an immutable frozen set.

        Validates that callers cannot mutate the shared catalogue and
        corrupt parsing for the rest of the process.
        """
        self.assertIsInstance(EnvironmentCaster.supportedTypes(), frozenset)

    def testReturnsTheSharedOptionsObject(self) -> None:
        """
        Return the shared class-level options object.

        Validates that the accessor performs no per-call allocation.
        """
        self.assertIs(EnvironmentCaster.supportedTypes(), EnvironmentCaster.OPTIONS)

# ---------------------------------------------------------------------------
# TestEnvironmentCasterParseTyped
# ---------------------------------------------------------------------------

class TestEnvironmentCasterParseTyped(TestCase):

    def testParsesIntegersWithoutBuildingACaster(self) -> None:
        """
        Parse an integer through the allocation-free fast path.

        Validates the primitive shortcut used whenever a typed entry is
        read back from the ``.env`` file.
        """
        self.assertEqual(EnvironmentCaster.parseTyped("int: 42 "), 42)

    def testRejectsAnUnparsableInteger(self) -> None:
        """
        Raise ValueError when the integer payload is malformed.

        Validates that the fast path reports the offending token instead
        of leaking the built-in conversion error.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster.parseTyped("int:abc")
        self.assertIn("Cannot convert 'abc' to int", str(ctx.exception))

    def testParsesFloatsWithoutBuildingACaster(self) -> None:
        """
        Parse a float through the allocation-free fast path.

        Validates the second primitive shortcut of the typed reader.
        """
        self.assertEqual(EnvironmentCaster.parseTyped("float: 3.5 "), 3.5)

    def testRejectsAnUnparsableFloat(self) -> None:
        """
        Raise ValueError when the float payload is malformed.

        Validates that the fast path reports the offending token instead
        of leaking the built-in conversion error.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster.parseTyped("float:abc")
        self.assertIn("Cannot convert 'abc' to float", str(ctx.exception))

    def testParsesEveryTruthyBooleanSpelling(self) -> None:
        """
        Parse every truthy spelling through the fast path.

        Validates the case-insensitive vocabulary accepted for boolean
        environment entries.
        """
        for word in _TRUE_WORDS:
            self.assertTrue(EnvironmentCaster.parseTyped(f"bool: {word.upper()} "))

    def testTreatsAnyOtherBooleanSpellingAsFalse(self) -> None:
        """
        Treat unknown boolean spellings as ``False`` on the fast path.

        Validates the documented asymmetry with the full parser, which
        instead rejects unknown spellings.
        """
        for word in (*_FALSE_WORDS, "maybe"):
            self.assertFalse(EnvironmentCaster.parseTyped(f"bool:{word}"))

    def testKeepsTrailingWhitespaceOnStrings(self) -> None:
        """
        Preserve trailing whitespace when parsing a string entry.

        Validates that only leading whitespace is trimmed, so padded
        values survive a write and read round trip.
        """
        self.assertEqual(EnvironmentCaster.parseTyped("str:  hello "), "hello ")

    def testDelegatesComplexTypesToTheFullCaster(self) -> None:
        """
        Delegate non-primitive hints to the full caster.

        Validates that containers, paths and base64 payloads still resolve
        through the slower but complete construction path.
        """
        self.assertEqual(EnvironmentCaster.parseTyped("list:[1, 2]"), [1, 2])
        self.assertEqual(EnvironmentCaster.parseTyped("dict:{'a': 1}"), {"a": 1})
        self.assertEqual(EnvironmentCaster.parseTyped("tuple:(1, 2)"), (1, 2))
        self.assertEqual(EnvironmentCaster.parseTyped("set:{1, 2}"), {1, 2})
        self.assertEqual(EnvironmentCaster.parseTyped("base64:aGVsbG8="), "hello")

# ---------------------------------------------------------------------------
# TestEnvironmentCasterConstruction
# ---------------------------------------------------------------------------

class TestEnvironmentCasterConstruction(TestCase):

    def testDetectsAKnownTypeHint(self) -> None:
        """
        Detect a known type hint written before the first colon.

        Validates the split that turns ``int:42`` into a hint plus its
        payload.
        """
        self.assertEqual(EnvironmentCaster("int:42").get(), 42)

    def testIgnoresSurroundingWhitespaceAroundTheHint(self) -> None:
        """
        Ignore whitespace and casing around the declared type hint.

        Validates that manually edited ``.env`` entries still resolve to
        the intended type.
        """
        self.assertEqual(EnvironmentCaster("  INT : 42").get(), 42)

    def testTreatsAnUnknownPrefixAsPartOfTheValue(self) -> None:
        """
        Treat an unknown prefix as ordinary value content.

        Validates that colon-bearing values such as URLs are never
        mistaken for a typed entry.
        """
        caster = EnvironmentCaster("https://example.test")
        self.assertEqual(caster.get(), "https://example.test")

    def testTreatsAColonFreeStringAsAPlainValue(self) -> None:
        """
        Treat a string without a colon as an untyped value.

        Validates the most common case of a plain textual variable.
        """
        self.assertEqual(EnvironmentCaster("plain").get(), "plain")

    def testStripsLeadingWhitespaceFromUntypedValues(self) -> None:
        """
        Strip leading whitespace from an untyped string value.

        Validates the normalisation applied before the hint lookup.
        """
        self.assertEqual(EnvironmentCaster("   plain").get(), "plain")

    def testKeepsNonStringInputsUntouched(self) -> None:
        """
        Keep non-string inputs exactly as they were supplied.

        Validates that values arriving from Python code, rather than from
        the ``.env`` file, are never re-parsed.
        """
        payload = [1, 2, 3]
        self.assertIs(EnvironmentCaster(payload).get(), payload)

    def testStoresNoneWhenTheTypedPayloadIsEmpty(self) -> None:
        """
        Store ``None`` when a typed entry carries no payload.

        Validates the guard that prevents an empty payload from being
        mistaken for an empty string.
        """
        with self.assertRaises(ValueError):
            EnvironmentCaster("int:").get()

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep caster instances free of an instance dictionary.

        Validates that the declared slots are effective, which requires
        the contract to declare empty slots as well.
        """
        self.assertFalse(hasattr(EnvironmentCaster("int:1"), "__dict__"))

# ---------------------------------------------------------------------------
# TestEnvironmentCasterGet
# ---------------------------------------------------------------------------

class TestEnvironmentCasterGet(TestCase):

    def testParsesEveryPrimitiveType(self) -> None:
        """
        Parse every primitive type declared by a hint.

        Validates the string, integer, float and boolean branches of the
        dispatch table.
        """
        self.assertEqual(EnvironmentCaster("str:  text ").get(), "text ")
        self.assertEqual(EnvironmentCaster("int: -7 ").get(), -7)
        self.assertEqual(EnvironmentCaster("float: -2.5 ").get(), -2.5)
        self.assertTrue(EnvironmentCaster("bool: TRUE ").get())

    def testParsesEveryTruthyBooleanSpelling(self) -> None:
        """
        Parse every truthy boolean spelling accepted by the parser.

        Validates the full vocabulary documented for boolean entries.
        """
        for word in _TRUE_WORDS:
            self.assertTrue(EnvironmentCaster(f"bool:{word}").get())

    def testParsesEveryFalsyBooleanSpelling(self) -> None:
        """
        Parse every falsy boolean spelling accepted by the parser.

        Validates the counterpart vocabulary of the truthy spellings.
        """
        for word in _FALSE_WORDS:
            self.assertFalse(EnvironmentCaster(f"bool:{word}").get())

    def testRejectsAnUnknownBooleanSpelling(self) -> None:
        """
        Raise ValueError for a boolean spelling outside the vocabulary.

        Validates that the full parser is stricter than the fast path and
        surfaces the accepted representations.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster("bool:maybe").get()
        self.assertIn("true/false", str(ctx.exception))

    def testRejectsUnparsableNumbers(self) -> None:
        """
        Raise ValueError when a numeric payload cannot be converted.

        Validates the parser error branches reached through the full
        dispatch table rather than the primitive fast path.
        """
        for entry, expected in (("int:abc", "to int"), ("float:abc", "to float")):
            with self.assertRaises(ValueError) as ctx:
                EnvironmentCaster(entry).get()
            self.assertIn(expected, str(ctx.exception))

    def testParsesEveryContainerType(self) -> None:
        """
        Parse every container type declared by a hint.

        Validates the list, dictionary, tuple and set branches evaluated
        through ``ast.literal_eval``.
        """
        self.assertEqual(EnvironmentCaster("list: [1, 2] ").get(), [1, 2])
        self.assertEqual(EnvironmentCaster("dict: {'a': 1} ").get(), {"a": 1})
        self.assertEqual(EnvironmentCaster("tuple: (1, 2) ").get(), (1, 2))
        self.assertEqual(EnvironmentCaster("set: {1, 2} ").get(), {1, 2})

    def testRejectsAContainerOfTheWrongShape(self) -> None:
        """
        Reject a payload whose literal does not match the declared hint.

        Validates that a dictionary declared as a list, and every other
        mismatched combination, is refused instead of silently accepted.
        """
        for entry in ("list:{'a': 1}", "dict:[1, 2]", "tuple:[1, 2]", "set:[1, 2]"):
            with self.assertRaises((TypeError, ValueError)):
                EnvironmentCaster(entry).get()

    def testRejectsAContainerWithInvalidSyntax(self) -> None:
        """
        Reject a container payload that is not a valid Python literal.

        Validates that a malformed ``.env`` entry fails loudly rather than
        returning a partially parsed value.
        """
        for entry in ("list:[1,", "dict:{'a':", "tuple:(1,", "set:{1,"):
            with self.assertRaises((SyntaxError, ValueError)):
                EnvironmentCaster(entry).get()

    def testReRaisesTypeErrorsWithTheOriginalType(self) -> None:
        """
        Preserve ``TypeError`` when the payload has the wrong shape.

        Validates that the error wrapper keeps the concrete exception type
        instead of collapsing everything into ``ValueError``.
        """
        with self.assertRaises(TypeError) as ctx:
            EnvironmentCaster("list:{'a': 1}").get()
        self.assertIn("type hint 'list'", str(ctx.exception))

    def testWrapsUnexpectedFailuresAsValueError(self) -> None:
        """
        Wrap unexpected failures into a ``ValueError``.

        Validates the last-resort handler that keeps the caster from
        leaking arbitrary exception types to its callers.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster("int:").get()
        self.assertIn("Error processing value", str(ctx.exception))

    def testDecodesBase64Payloads(self) -> None:
        """
        Decode a base64 payload back into readable text.

        Validates the round trip used by ``APP_KEY`` style secrets.
        """
        self.assertEqual(EnvironmentCaster("base64:aGVsbG8=").get(), "hello")

    def testReturnsRawBytesForNonTextualBase64Payloads(self) -> None:
        """
        Return raw bytes when the decoded payload is not UTF-8 text.

        Validates that binary secrets survive decoding without being
        mangled by a lossy conversion.
        """
        encoded = base64.b64encode(_NON_UTF8).decode("utf-8")
        self.assertEqual(EnvironmentCaster(f"base64:{encoded}").get(), _NON_UTF8)

    def testDecodesBase64PayloadsHeldAsBytes(self) -> None:
        """
        Decode a base64 payload that is stored as raw bytes.

        Validates the normalisation applied when the value was supplied by
        Python code rather than parsed from the ``.env`` file.
        """
        caster = EnvironmentCaster(b"aGVsbG8=")
        caster.to("base64")
        self.assertEqual(caster.get(), "hello")

    def testRejectsAMalformedBase64Payload(self) -> None:
        """
        Raise ValueError when the base64 payload cannot be decoded.

        Validates that a truncated or corrupted secret is reported instead
        of producing garbage bytes.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster("base64:not-base64!").get()
        self.assertIn("Cannot decode Base64 value", str(ctx.exception))

    def testNormalisesPathSeparators(self) -> None:
        """
        Normalise Windows separators into POSIX form.

        Validates that a path written on any platform is read back with a
        single, portable representation.
        """
        caster = EnvironmentCaster("path:C:\\\\data\\\\logs")
        self.assertNotIn("\\", str(caster.get()))

    def testReturnsPosixFormForPathObjects(self) -> None:
        """
        Return the POSIX form when the value already is a path object.

        Validates the shortcut that avoids re-parsing a value produced by
        Python code.
        """
        caster = EnvironmentCaster(Path("/var/log/app"))
        caster.to("path")
        self.assertEqual(caster.get(), "/var/log/app")

    def testWrapsPathConversionFailures(self) -> None:
        """
        Wrap path conversion failures into a ``ValueError``.

        Validates the defensive handler protecting the caller from values
        that cannot be rendered as text.
        """
        caster = build_caster("path", _UnprintableOnceValue())
        with self.assertRaises(ValueError) as ctx:
            caster.get()
        self.assertIn("to path", str(ctx.exception))

    def testReturnsTheRawValueWhenNoHintIsDeclared(self) -> None:
        """
        Return the raw value when no type hint was detected.

        Validates the untyped shortcut of the dispatch table.
        """
        self.assertEqual(EnvironmentCaster("plain value").get(), "plain value")

    def testReturnsTheRawValueForAnUndispatchedHint(self) -> None:
        """
        Return the raw value when the hint has no dispatch branch.

        Validates the defensive fallback that keeps the caster usable if
        the supported options are extended without a matching parser.
        """
        self.assertEqual(_ExtendedCaster("unknown:payload").get(), "payload")

# ---------------------------------------------------------------------------
# TestEnvironmentCasterTo
# ---------------------------------------------------------------------------

class TestEnvironmentCasterTo(TestCase):

    def testSerialisesEveryPrimitiveType(self) -> None:
        """
        Serialise every primitive type with its hint prefix.

        Validates the representation written back to the ``.env`` file for
        strings, integers, floats and booleans.
        """
        self.assertEqual(EnvironmentCaster("text").to("str"), "str:text")
        self.assertEqual(EnvironmentCaster(42).to("int"), "int:42")
        self.assertEqual(EnvironmentCaster(2.5).to("float"), "float:2.5")
        self.assertEqual(EnvironmentCaster(True).to("bool"), "bool:true")
        self.assertEqual(EnvironmentCaster(False).to("bool"), "bool:false")

    def testSerialisesEveryContainerType(self) -> None:
        """
        Serialise every container type with its hint prefix.

        Validates that the stored representation is the Python literal
        expected by the matching parser.
        """
        self.assertEqual(EnvironmentCaster([1, 2]).to("list"), "list:[1, 2]")
        self.assertEqual(EnvironmentCaster({"a": 1}).to("dict"), "dict:{'a': 1}")
        self.assertEqual(EnvironmentCaster((1, 2)).to("tuple"), "tuple:(1, 2)")
        self.assertEqual(EnvironmentCaster({1}).to("set"), "set:{1}")

    def testAcceptsAnEnumerationHint(self) -> None:
        """
        Accept the target type expressed as an enumeration member.

        Validates that callers may use ``EnvironmentValueType`` instead of
        raw strings when declaring a type.
        """
        caster = EnvironmentCaster(42)
        self.assertEqual(caster.to(EnvironmentValueType.INT), "int:42")

    def testConvertsTextualNumbersToTheirDeclaredType(self) -> None:
        """
        Convert textual numbers into their declared numeric type.

        Validates the usability branch that accepts a string when an
        integer or a float was declared.
        """
        self.assertEqual(EnvironmentCaster(" 42 ").to("int"), "int:42")
        self.assertEqual(EnvironmentCaster(" 2.5 ").to("float"), "float:2.5")

    def testConvertsCompatibleNumbersAcrossTypes(self) -> None:
        """
        Convert compatible numbers across the numeric hints.

        Validates the direct coercion branch used when an integer is
        declared as a float, and the opposite case.
        """
        self.assertEqual(EnvironmentCaster(42).to("float"), "float:42.0")
        self.assertEqual(EnvironmentCaster(2.9).to("int"), "int:2")

    def testRejectsTextualNumbersThatCannotBeConverted(self) -> None:
        """
        Reject textual payloads that are not valid numbers.

        Validates that a malformed declaration fails at write time rather
        than at the next read.
        """
        for type_hint in ("int", "float"):
            with self.assertRaises(ValueError):
                EnvironmentCaster("abc").to(type_hint)

    def testRejectsValuesThatCannotBecomeNumbers(self) -> None:
        """
        Reject non-textual values that cannot become numbers.

        Validates the last coercion branch of the numeric serialisers.
        """
        for type_hint in ("int", "float"):
            with self.assertRaises(ValueError) as ctx:
                EnvironmentCaster([1, 2]).to(type_hint)
            self.assertIn("must be convertible", str(ctx.exception))

    def testSerialisesEveryTextualBooleanSpelling(self) -> None:
        """
        Serialise every textual boolean spelling to a canonical form.

        Validates that all accepted spellings collapse into ``true`` or
        ``false`` before being written.
        """
        for word in _TRUE_WORDS:
            self.assertEqual(EnvironmentCaster(word).to("bool"), "bool:true")
        for word in _FALSE_WORDS:
            self.assertEqual(EnvironmentCaster(word).to("bool"), "bool:false")

    def testRejectsAnUnknownTextualBoolean(self) -> None:
        """
        Reject a textual boolean outside the accepted vocabulary.

        Validates that ambiguous values never reach the ``.env`` file.
        """
        with self.assertRaises(ValueError):
            EnvironmentCaster("maybe").to("bool")

    def testFallsBackToTruthinessForOtherTypes(self) -> None:
        """
        Fall back to Python truthiness for non-textual values.

        Validates the branch used when an arbitrary object is declared as
        a boolean.
        """
        self.assertEqual(EnvironmentCaster([1, 2]).to("bool"), "bool:true")
        self.assertEqual(EnvironmentCaster([]).to("bool"), "bool:false")

    def testRejectsValuesWithoutATruthValue(self) -> None:
        """
        Reject values that refuse the truthiness protocol.

        Validates the defensive handler around the truthiness fallback.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster(_UncoercibleValue()).to("bool")
        self.assertIn("must be convertible to boolean", str(ctx.exception))

    def testRejectsMismatchedContainerTypes(self) -> None:
        """
        Reject values whose type does not match the declared container.

        Validates the guards of the list, dictionary, tuple and set
        serialisers.
        """
        for type_hint in ("list", "dict", "tuple", "set"):
            with self.assertRaises(ValueError) as ctx:
                EnvironmentCaster("text").to(type_hint)
            self.assertIn(f"to convert to {type_hint}", str(ctx.exception))

    def testRejectsNonTextualStringValues(self) -> None:
        """
        Reject non-textual values declared as a string.

        Validates that the string serialiser never coerces silently.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster(42).to("str")
        self.assertIn("must be a string", str(ctx.exception))

    def testResolvesRelativePathsAgainstTheWorkingDirectory(self) -> None:
        """
        Resolve a relative path against the current working directory.

        Validates that stored paths are always absolute and therefore
        independent of the process that reads them later.
        """
        stored = EnvironmentCaster("logs/app.log").to("path")
        self.assertTrue(stored.startswith("path:"))
        self.assertTrue(Path(stored.removeprefix("path:")).is_absolute())

    def testKeepsAbsolutePathsUnchanged(self) -> None:
        """
        Keep an already absolute path unchanged.

        Validates that the working directory is never prepended twice.
        """
        absolute = Path.cwd() / "logs"
        stored = EnvironmentCaster(absolute).to("path")
        self.assertEqual(stored, f"path:{absolute.as_posix()}")

    def testNormalisesWindowsSeparatorsWhenStoringPaths(self) -> None:
        """
        Normalise Windows separators when storing a path.

        Validates that the persisted representation is always POSIX.
        """
        stored = EnvironmentCaster("\\\\var\\\\log").to("path")
        self.assertNotIn("\\", stored)

    def testRejectsValuesThatAreNotPathLike(self) -> None:
        """
        Reject values that are neither strings nor path objects.

        Validates the type guard of the path serialiser.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster(42).to("path")
        self.assertIn("must be a string or Path", str(ctx.exception))

    def testPreservesValuesThatAlreadyAreBase64(self) -> None:
        """
        Preserve a payload that already is valid base64.

        Validates that re-writing an existing secret never double encodes
        it.
        """
        self.assertEqual(
            EnvironmentCaster("aGVsbG8=").to("base64"),
            "base64:aGVsbG8=",
        )

    def testEncodesTextualPayloadsIntoBase64(self) -> None:
        """
        Encode a plain textual payload into base64.

        Validates the branch taken when the value is not already encoded.
        """
        self.assertEqual(
            EnvironmentCaster("hi!").to("base64"),
            f"base64:{base64.b64encode(b'hi!').decode('utf-8')}",
        )

    def testEncodesBinaryPayloadsIntoBase64(self) -> None:
        """
        Encode a raw bytes payload into base64.

        Validates the branch that skips the UTF-8 encoding step because
        the value already is binary.
        """
        self.assertEqual(
            EnvironmentCaster(b"hello").to("base64"),
            f"base64:{base64.b64encode(b'hello').decode('utf-8')}",
        )

    def testRejectsBinaryPayloadsThatAreNotUtf8(self) -> None:
        """
        Reject binary payloads that cannot be decoded as UTF-8.

        Validates the guard placed before the base64 validity check.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster(_NON_UTF8).to("base64")
        self.assertIn("Cannot decode bytes to UTF-8", str(ctx.exception))

    def testRejectsTextualPayloadsThatCannotBeEncoded(self) -> None:
        """
        Reject textual payloads that cannot be encoded as UTF-8.

        Validates the handler around the base64 encoding step, reachable
        with an unpaired surrogate.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster(_LONE_SURROGATE).to("base64")
        self.assertIn("Error during Base64 encoding", str(ctx.exception))

    def testRejectsValuesThatCannotBecomeBase64(self) -> None:
        """
        Reject values that are neither strings nor bytes.

        Validates the type guard of the base64 serialiser.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster(42).to("base64")
        self.assertIn("must be a string or bytes", str(ctx.exception))

    def testRejectsAnUnsupportedTypeHint(self) -> None:
        """
        Reject a type hint outside the supported catalogue.

        Validates the guard that runs before any serialisation work.
        """
        with self.assertRaises(ValueError) as ctx:
            EnvironmentCaster("text").to("decimal")
        self.assertIn("Invalid type hint", str(ctx.exception))

    def testRejectsASupportedHintWithoutASerialiser(self) -> None:
        """
        Reject a supported hint that has no serialiser branch.

        Validates the defensive fallback that keeps the caster safe if the
        supported options are extended without a matching serialiser.
        """
        with self.assertRaises(ValueError) as ctx:
            _ExtendedCaster("text").to("unknown")
        self.assertIn("is not supported for conversion", str(ctx.exception))

# ---------------------------------------------------------------------------
# TestEnvironmentCasterRoundTrip
# ---------------------------------------------------------------------------

class TestEnvironmentCasterRoundTrip(TestCase):

    def testRestoresEveryValueThroughAFullRoundTrip(self) -> None:
        """
        Restore every supported value through a write and read cycle.

        Validates that the serialiser and the parser agree on the stored
        representation for the whole type catalogue.
        """
        for value, type_hint in (
            ("text", "str"),
            (42, "int"),
            (2.5, "float"),
            (True, "bool"),
            ([1, 2], "list"),
            ({"a": 1}, "dict"),
            ((1, 2), "tuple"),
            ({1, 2}, "set"),
            ("secret", "base64"),
        ):
            stored = EnvironmentCaster(value).to(type_hint)
            self.assertEqual(EnvironmentCaster.parseTyped(stored), value)
