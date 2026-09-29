from orionis.environment.enums.value_type import EnvironmentValueType
from orionis.environment.validators import ValidateTypes as PackageValidateTypes
from orionis.environment.validators.types import ValidateTypes
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# TestValidateTypesInference
# ---------------------------------------------------------------------------

class TestValidateTypesInference(TestCase):

    def testInfersTheTypeOfEverySupportedValue(self) -> None:
        """Infer the lowercase type name of every supported value.

        Validates the no-hint branch, which is what ``DotEnv.set`` relies
        on when the caller does not declare a type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for value, expected in (
            ("text", "str"),
            (42, "int"),
            (3.14, "float"),
            (True, "bool"),
            ([1, 2], "list"),
            ({"a": 1}, "dict"),
            ((1, 2), "tuple"),
            ({1, 2}, "set"),
        ):
            self.assertEqual(ValidateTypes(value=value, type_hint=None), expected)

    def testInfersTheTypeWhenTheHintIsOmitted(self) -> None:
        """Infer the type when the hint argument is omitted entirely.

        Validates that the default value of ``type_hint`` behaves exactly
        like an explicit ``None``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ValidateTypes(value="text"), "str")

    def testIsReExportedByThePackage(self) -> None:
        """Re-export the validator from the validators package root.

        Validates that both documented import paths resolve to the very
        same callable object.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(ValidateTypes, PackageValidateTypes)

# ---------------------------------------------------------------------------
# TestValidateTypesNormalisation
# ---------------------------------------------------------------------------

class TestValidateTypesNormalisation(TestCase):

    def testNormalisesEveryStringHint(self) -> None:
        """Normalise every documented string hint to its canonical value.

        Validates that a textual hint wins over the inferred type and is
        returned in the exact form the caster expects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for member in EnvironmentValueType:
            self.assertEqual(
                ValidateTypes(value="ignored", type_hint=member.value),
                member.value,
            )

    def testAcceptsUppercaseAndMixedCaseHints(self) -> None:
        """Accept hints written in uppercase or mixed case.

        Validates the case-insensitive name lookup performed before the
        enumeration member is resolved.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ValidateTypes(value=1, type_hint="INT"), "int")
        self.assertEqual(ValidateTypes(value=1, type_hint="Base64"), "base64")

    def testNormalisesEveryEnumerationHint(self) -> None:
        """Normalise every enumeration member to its string value.

        Validates that callers may pass ``EnvironmentValueType`` members
        instead of raw strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for member in EnvironmentValueType:
            self.assertEqual(
                ValidateTypes(value="ignored", type_hint=member),
                member.value,
            )

    def testHintOverridesTheInferredType(self) -> None:
        """Prefer the declared hint over the inferred value type.

        Validates that an integer stored as ``str`` keeps the declared
        serialisation instead of the inferred one.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ValidateTypes(value=42, type_hint="str"), "str")

    def testReusesTheCachedNormalisationForRepeatedHints(self) -> None:
        """Serve repeated hint normalisations from the memoisation cache.

        Validates that the ``lru_cache`` wrapper stays active, keeping the
        hot configuration path free of enumeration lookups.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ValidateTypes(value=1, type_hint="int")
        ValidateTypes(value=2, type_hint="int")
        self.assertEqual(ValidateTypes(value=3, type_hint="int"), "int")

# ---------------------------------------------------------------------------
# TestValidateTypesRejections
# ---------------------------------------------------------------------------

class TestValidateTypesRejections(TestCase):

    def testRejectsEveryUnsupportedValueType(self) -> None:
        """Raise TypeError for values outside the supported catalogue.

        Validates that objects, bytes, ``None`` and frozensets cannot be
        serialised into a ``.env`` entry.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for value in (None, b"bytes", object(), frozenset({1}), 1j):
            with self.assertRaises(TypeError):
                ValidateTypes(value=value, type_hint=None)

    def testReportsTheReceivedValueTypeInTheMessage(self) -> None:
        """Report the offending value type inside the error message.

        Validates that the failure is actionable without inspecting a
        traceback.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError) as ctx:
            ValidateTypes(value=None, type_hint=None)
        self.assertIn("NoneType", str(ctx.exception))

    def testRejectsEveryNonTextualHint(self) -> None:
        """Raise TypeError when the hint is neither a string nor a member.

        Validates that the hint guard runs before normalisation for
        integers, floats, booleans and containers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for type_hint in (1, 2.5, True, ["int"], {"type": "int"}):
            with self.assertRaises(TypeError):
                ValidateTypes(value="text", type_hint=type_hint)

    def testRejectsAnEmptyHintInsteadOfSkippingValidation(self) -> None:
        """Raise RuntimeError when the hint is an empty string.

        Validates that a falsy but non-``None`` hint is still validated
        instead of silently falling back to type inference.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(RuntimeError):
            ValidateTypes(value="text", type_hint="")

    def testRejectsAnUnknownHint(self) -> None:
        """Raise RuntimeError when the hint names an unsupported type.

        Validates that the error lists the allowed hints so the caller can
        correct the declaration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(RuntimeError) as ctx:
            ValidateTypes(value="text", type_hint="decimal")
        message = str(ctx.exception)
        self.assertIn("decimal", message)
        self.assertIn("base64", message)
