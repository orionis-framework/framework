from orionis.environment.validators import ValidateKeyName as PackageValidateKeyName
from orionis.environment.validators.key_name import ValidateKeyName
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# TestValidateKeyNameAcceptedNames
# ---------------------------------------------------------------------------

class TestValidateKeyNameAcceptedNames(TestCase):

    def testAcceptsEveryValidNamingShape(self) -> None:
        """
        Accept every documented shape of a valid variable name.

        Validates the single uppercase letter, plain word, underscored,
        digit-suffixed, mixed and consecutive-underscore forms allowed by
        the pattern.
        """
        for key in (
            "A",
            "HELLO",
            "MY_VAR",
            "VAR123",
            "A1_B2_C3",
            "A__B",
            "DATABASE_CONNECTION_POOL_SIZE",
        ):
            self.assertEqual(ValidateKeyName(key), key)

    def testReturnsTheValidatedNameUnchanged(self) -> None:
        """
        Return the very same string object that was validated.

        Validates that no normalisation or copying happens, so callers can
        rely on identity when caching keys.
        """
        key = "MY_KEY"
        self.assertIs(ValidateKeyName(key), key)

    def testIsReExportedByThePackage(self) -> None:
        """
        Re-export the validator from the validators package root.

        Validates that both documented import paths resolve to the very
        same callable.
        """
        self.assertIs(ValidateKeyName, PackageValidateKeyName)

# ---------------------------------------------------------------------------
# TestValidateKeyNameRejectedTypes
# ---------------------------------------------------------------------------

class TestValidateKeyNameRejectedTypes(TestCase):

    def testRejectsEveryNonStringInput(self) -> None:
        """
        Raise TypeError for every non-string input.

        Validates that the type guard runs before the pattern check for
        integers, floats, booleans, ``None`` and containers.
        """
        for key in (42, 3.14, True, None, ["KEY"], {"KEY": 1}, ("KEY",)):
            with self.assertRaises(TypeError):
                ValidateKeyName(key)

    def testReportsTheReceivedTypeInTheMessage(self) -> None:
        """
        Report the offending type inside the error message.

        Validates that the failure is actionable without inspecting a
        traceback.
        """
        with self.assertRaises(TypeError) as ctx:
            ValidateKeyName(42)
        self.assertIn("int", str(ctx.exception))

# ---------------------------------------------------------------------------
# TestValidateKeyNameRejectedNames
# ---------------------------------------------------------------------------

class TestValidateKeyNameRejectedNames(TestCase):

    def testRejectsEveryNameOutsideThePattern(self) -> None:
        """
        Raise ValueError for every name outside the allowed pattern.

        Validates rejection of empty names, lowercase letters, a leading
        digit or underscore, whitespace, hyphens, dots and any character
        that is not an uppercase letter, digit or underscore.
        """
        for key in (
            "",
            "lower",
            "Mixed_Case",
            "1VAR",
            "_VAR",
            "MY VAR",
            "MY-VAR",
            "MY.VAR",
            "MY_VAR\n",
            "VÄR",
        ):
            with self.assertRaises(ValueError):
                ValidateKeyName(key)

    def testReportsTheOffendingNameInTheMessage(self) -> None:
        """
        Report the offending name inside the error message.

        Validates that the failure names the rejected key and documents
        the expected convention.
        """
        with self.assertRaises(ValueError) as ctx:
            ValidateKeyName("lower")
        message = str(ctx.exception)
        self.assertIn("lower", message)
        self.assertIn("MY_ENV_VAR", message)

# ---------------------------------------------------------------------------
# TestValidateKeyNameCaching
# ---------------------------------------------------------------------------

class TestValidateKeyNameCaching(TestCase):

    def testReusesTheCachedResultForRepeatedNames(self) -> None:
        """
        Serve repeated validations from the memoisation cache.

        Validates that the ``lru_cache`` wrapper is active, which keeps
        the hot configuration path free of regex matching.
        """
        info_before = ValidateKeyName.cache_info()
        ValidateKeyName("CACHED_KEY")
        ValidateKeyName("CACHED_KEY")
        info_after = ValidateKeyName.cache_info()
        self.assertGreater(info_after.hits, info_before.hits)
