from orionis.http.payload.media_types import MediaTypeRegistry
from orionis.http.payload.parsers import parse_json, parse_text
from orionis.test import TestCase

class TestMediaTypeRegistryInit(TestCase):
    """Verify MediaTypeRegistry initialisation."""

    def testEmptyRegistryReturnsNoneForAnyType(self) -> None:
        """
        Verify that an uninitialised registry returns None for all lookups.

        Confirms that get() returns None when no parsers have been
        registered.
        """
        registry = MediaTypeRegistry()
        self.assertIsNone(registry.get("application/json"))

    def testInitWithParsersDict(self) -> None:
        """
        Verify that parsers passed to the constructor are registered.

        Confirms that a parser provided via the initial dict is accessible
        immediately after construction.
        """
        registry = MediaTypeRegistry({"application/json": parse_json})
        self.assertIs(registry.get("application/json"), parse_json)

    def testInitKeysAreLowercased(self) -> None:
        """
        Verify that constructor keys are normalised to lowercase.

        Confirms that 'Application/JSON' is stored as 'application/json'.
        """
        registry = MediaTypeRegistry({"Application/JSON": parse_json})
        self.assertIs(registry.get("application/json"), parse_json)

    def testNoneInitCreatesEmptyRegistry(self) -> None:
        """
        Verify that passing None to the constructor creates an empty registry.

        Confirms the explicit None branch does not raise.
        """
        registry = MediaTypeRegistry(None)
        self.assertIsNone(registry.get("text/plain"))

class TestMediaTypeRegistryRegister(TestCase):
    """Verify MediaTypeRegistry.register()."""

    def testRegisterAddsParser(self) -> None:
        """
        Verify that register() makes the parser accessible via get().

        Confirms that a newly registered media type is returned by get().
        """
        registry = MediaTypeRegistry()
        registry.register("text/plain", parse_text)
        self.assertIs(registry.get("text/plain"), parse_text)

    def testRegisterOverwritesExistingParser(self) -> None:
        """
        Verify that register() replaces an existing parser for the same type.

        Confirms that the last registered parser wins.
        """
        registry = MediaTypeRegistry({"text/plain": parse_text})
        registry.register("text/plain", parse_json)
        self.assertIs(registry.get("text/plain"), parse_json)

    def testRegisterKeyIsCaseInsensitive(self) -> None:
        """
        Verify that register() normalises the media-type key to lowercase.

        Confirms that 'TEXT/PLAIN' is stored and retrieved as 'text/plain'.
        """
        registry = MediaTypeRegistry()
        registry.register("TEXT/PLAIN", parse_text)
        self.assertIs(registry.get("text/plain"), parse_text)

class TestMediaTypeRegistryGet(TestCase):
    """Verify MediaTypeRegistry.get()."""

    def testGetReturnsParserlForRegisteredType(self) -> None:
        """
        Verify that get() returns the correct parser for a registered type.

        Confirms that the exact parser object is returned by identity.
        """
        registry = MediaTypeRegistry({"application/json": parse_json})
        self.assertIs(registry.get("application/json"), parse_json)

    def testGetIsCaseInsensitive(self) -> None:
        """
        Verify that get() normalises the lookup key to lowercase.

        Confirms that 'APPLICATION/JSON' matches 'application/json'.
        """
        registry = MediaTypeRegistry({"application/json": parse_json})
        self.assertIs(registry.get("APPLICATION/JSON"), parse_json)

    def testGetReturnsNoneForUnknownType(self) -> None:
        """
        Verify that get() returns None for an unregistered media type.

        Confirms the sentinel-return contract when no parser is found.
        """
        registry = MediaTypeRegistry()
        self.assertIsNone(registry.get("application/x-custom"))

class TestMediaTypeRegistryExtend(TestCase):
    """Verify MediaTypeRegistry.extend()."""

    def testExtendReturnNewRegistry(self) -> None:
        """
        Verify that extend() returns a new MediaTypeRegistry instance.

        Confirms that the return value is a different object from the
        original registry.
        """
        registry = MediaTypeRegistry({"text/plain": parse_text})
        extended = registry.extend({"application/json": parse_json})
        self.assertIsNot(extended, registry)

    def testOriginalRegistryIsNotMutated(self) -> None:
        """
        Verify that the original registry is unchanged after extend().

        Confirms that the new entries are not written back to the source.
        """
        registry = MediaTypeRegistry({"text/plain": parse_text})
        registry.extend({"application/json": parse_json})
        self.assertIsNone(registry.get("application/json"))

    def testExtendedRegistryContainsOriginalEntries(self) -> None:
        """
        Verify that the extended registry contains entries from the original.

        Confirms that existing parsers survive the merge operation.
        """
        registry = MediaTypeRegistry({"text/plain": parse_text})
        extended = registry.extend({"application/json": parse_json})
        self.assertIs(extended.get("text/plain"), parse_text)

    def testExtendedRegistryContainsNewEntries(self) -> None:
        """
        Verify that the extended registry contains the newly added entries.

        Confirms that parsers passed to extend() appear in the result.
        """
        registry = MediaTypeRegistry()
        extended = registry.extend({"application/json": parse_json})
        self.assertIs(extended.get("application/json"), parse_json)

    def testExtendOverwritesExistingKeys(self) -> None:
        """
        Verify that extend() overwrites existing keys in the merged registry.

        Confirms that the new parsers dict takes precedence over originals
        when the same key exists in both.
        """
        registry = MediaTypeRegistry({"text/plain": parse_text})
        extended = registry.extend({"text/plain": parse_json})
        self.assertIs(extended.get("text/plain"), parse_json)
