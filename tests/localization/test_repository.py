from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.contracts.repository import ITranslationRepository
from orionis.localization.repository import TranslationRepository
from orionis.test import TestCase

class _RecordingLoader(ITranslationLoader):
    """Loader double recording every locale read from disk."""

    __slots__ = ("calls", "payloads")

    def __init__(self, payloads: dict[str, dict[str, str]]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []

    def load(self, locale: str) -> dict[str, str]:
        """
        Return the configured payload for *locale*.

        Parameters
        ----------
        locale : str
            Locale code requested by the repository.

        Returns
        -------
        dict[str, str]
            Configured translation map, empty when not configured.
        """
        self.calls.append(locale)
        return dict(self.payloads.get(locale, {}))

    def availableLocales(self) -> tuple[str, ...]:
        """
        Return the locales configured on the double.

        Returns
        -------
        tuple[str, ...]
            Sorted locale codes known by the double.
        """
        return tuple(sorted(self.payloads))

class _RepositoryFixture(TestCase):
    """Provide a repository backed by a recording loader."""

    def setUp(self) -> None:
        """
        Build a repository over a deterministic loader double.

        Guarantees that cache behaviour is observed without touching the
        file system.

        Returns
        -------
        None
        """
        self._loader = _RecordingLoader({
            "es": {"Welcome": "Bienvenido"},
            "en": {"Welcome": "Welcome"},
        })
        self._repository = TranslationRepository(self._loader)

class TestTranslationRepositoryDefinition(_RepositoryFixture):
    """Validate the structural contract of the repository."""

    def testImplementsTheRepositoryContract(self) -> None:
        """
        Implement the declared repository contract.

        Validates that the cache can be injected wherever the contract
        is required.
        """
        self.assertIsInstance(self._repository, ITranslationRepository)

    def testInstancesDoNotCarryAnInstanceDictionary(self) -> None:
        """
        Keep repository instances free of an instance dictionary.

        Validates that the declared slots are effective, which requires
        the contract to declare empty slots as well.
        """
        self.assertFalse(hasattr(self._repository, "__dict__"))

class TestTranslationRepositoryCaching(_RepositoryFixture):
    """Validate that every locale is read from disk at most once."""

    def testLocaleIsReadFromTheLoaderOnlyOnce(self) -> None:
        """
        Read a locale from the loader exactly once.

        Validates the caching guarantee that makes repeated lookups
        purely in-memory operations.
        """
        first = self._repository.get("es")
        self.assertIs(self._repository.get("es"), first)
        self.assertEqual(self._loader.calls, ["es"])

    def testEmptyResultsAreCachedAsWell(self) -> None:
        """
        Cache a locale that resolves to an empty map.

        Validates that unknown locales do not trigger a disk read on
        every single lookup.
        """
        self.assertEqual(self._repository.get("fr"), {})
        self.assertEqual(self._repository.get("fr"), {})
        self.assertEqual(self._loader.calls, ["fr"])

    def testEachLocaleIsCachedIndependently(self) -> None:
        """
        Keep one cache entry per locale.

        Validates that loading a second locale never evicts or shadows
        the first one.
        """
        self.assertEqual(self._repository.get("es")["Welcome"], "Bienvenido")
        self.assertEqual(self._repository.get("en")["Welcome"], "Welcome")
        self.assertEqual(self._loader.calls, ["es", "en"])

    def testGetReturnsTheCachedMappingItself(self) -> None:
        """
        Return the cached mapping instead of a defensive copy.

        Validates the documented contract that mutating the returned
        mapping mutates the cache for every consumer.
        """
        translations = self._repository.get("es")
        translations["Welcome"] = "Hola"
        self.assertEqual(self._repository.get("es")["Welcome"], "Hola")
        self.assertEqual(self._loader.calls, ["es"])

class TestTranslationRepositoryInspection(_RepositoryFixture):
    """Validate the introspection helpers of the cache."""

    def testHasReportsOnlyCachedLocales(self) -> None:
        """
        Report as cached only the locales already loaded.

        Validates that inspection never triggers a load by itself.
        """
        self.assertFalse(self._repository.has("es"))
        self._repository.get("es")
        self.assertTrue(self._repository.has("es"))
        self.assertEqual(self._loader.calls, ["es"])

    def testLoadedLocalesPreservesInsertionOrder(self) -> None:
        """
        List cached locales in load order.

        Validates that the reported order mirrors the sequence in which
        the locales were requested.
        """
        self._repository.get("es")
        self._repository.get("en")
        self.assertEqual(self._repository.loadedLocales(), ("es", "en"))

class TestTranslationRepositoryEviction(_RepositoryFixture):
    """Validate cache invalidation of one or every locale."""

    def testForgetRemovesTheCachedLocale(self) -> None:
        """
        Drop the cache entry of a single locale.

        Validates that the next lookup reads the source again.
        """
        self._repository.get("es")
        self.assertTrue(self._repository.forget("es"))
        self.assertFalse(self._repository.has("es"))
        self._repository.get("es")
        self.assertEqual(self._loader.calls, ["es", "es"])

    def testForgetReportsFalseForUncachedLocales(self) -> None:
        """
        Report that nothing was evicted for an uncached locale.

        Validates the boolean contract used by callers to detect a
        no-op invalidation.
        """
        self.assertFalse(self._repository.forget("es"))

    def testFlushDiscardsEveryCachedLocale(self) -> None:
        """
        Drop every cache entry at once.

        Validates the bulk invalidation used when translations change
        on disk.
        """
        self._repository.get("es")
        self._repository.get("en")
        self._repository.flush()
        self.assertEqual(self._repository.loadedLocales(), ())
        self.assertFalse(self._repository.has("en"))
