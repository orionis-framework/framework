import tempfile
from pathlib import Path
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.exceptions import InvalidLocaleException
from orionis.localization.manager import LocalizationManager
from orionis.test import TestCase

class _StubApp:
    """Application double exposing a base path and configuration values."""

    __slots__ = ("_base_path", "_config", "requested")

    def __init__(self, base_path: Path, config: dict[str, object]) -> None:
        self._base_path = base_path
        self._config = config
        self.requested: list[str] = []

    @property
    def basePath(self) -> Path:
        """
        Return the application base path.

        Returns
        -------
        Path
            Directory acting as the application root.
        """
        return self._base_path

    def config(self, key: str) -> object:
        """
        Return the configured value stored under *key*.

        Parameters
        ----------
        key : str
            Dot-notated configuration key requested by the manager.

        Returns
        -------
        object
            Configured value, or None when the key is absent.
        """
        self.requested.append(key)
        return self._config.get(key)

class _ManagerFixture(TestCase):
    """Provide an application double over a temporary project tree."""

    def setUp(self) -> None:
        """
        Create a temporary application root with language sources.

        Guarantees that every test resolves paths against its own
        project tree.

        Returns
        -------
        None
        """
        self._temporary = tempfile.TemporaryDirectory()
        self._base = Path(self._temporary.name)
        self._writeSource(self._base / "resources" / "lang", "es", "Bienvenido")
        self._writeSource(self._base / "resources" / "lang", "en", "Welcome")

    def tearDown(self) -> None:
        """
        Remove the temporary application root.

        Guarantees that no fixture file survives the test that created
        it.

        Returns
        -------
        None
        """
        self._temporary.cleanup()

    def _writeSource(self, directory: Path, locale: str, line: str) -> None:
        """
        Write a single-entry translation file for *locale*.

        Parameters
        ----------
        directory : Path
            Language directory receiving the file.
        locale : str
            Locale code used as the file name.
        line : str
            Translation registered under the ``Welcome`` key.

        Returns
        -------
        None
        """
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{locale}.json").write_text(
            f'{{"Welcome": "{line}"}}',
            encoding="utf-8",
        )

    def _makeManager(self, config: dict[str, object]) -> LocalizationManager:
        """
        Build a manager over an application double.

        Parameters
        ----------
        config : dict[str, object]
            Configuration values exposed to the manager.

        Returns
        -------
        LocalizationManager
            Manager bound to the temporary application root.
        """
        self._app = _StubApp(self._base, config)
        return LocalizationManager(self._app)

class TestLocalizationManagerDefinition(_ManagerFixture):
    """Validate the structural contract of the manager."""

    def testImplementsTheManagerContract(self) -> None:
        """
        Implement the declared manager contract.

        Validates that the manager can be resolved through its contract
        by the container.
        """
        manager = self._makeManager({})
        self.assertIsInstance(manager, ILocalizationManager)

    def testInstancesDoNotCarryAnInstanceDictionary(self) -> None:
        """
        Keep manager instances free of an instance dictionary.

        Validates that the declared slots are effective, which requires
        the contract to declare empty slots as well.
        """
        self.assertFalse(hasattr(self._makeManager({}), "__dict__"))

class TestLocalizationManagerWiring(_ManagerFixture):
    """Validate translator construction from the configuration."""

    def testBuildsATranslatorFromTheConfiguredSettings(self) -> None:
        """
        Build a translator honouring the configured settings.

        Validates that locale, fallback locale, and language path are
        read from the application configuration.
        """
        manager = self._makeManager({
            "app.locale": "es",
            "app.fallback_locale": "en",
            "app.language_path": "resources/lang/",
        })
        translator = manager.translator()
        self.assertEqual(translator.getLocale(), "es")
        self.assertEqual(translator.get("Welcome"), "Bienvenido")
        self.assertEqual(translator.availableLocales(), ("en", "es"))

    def testTranslatorIsBuiltOnceAndShared(self) -> None:
        """
        Reuse a single translator across the application.

        Validates that the configuration is read once and that the
        translation cache is shared by every consumer.
        """
        manager = self._makeManager({"app.locale": "es"})
        translator = manager.translator()
        self.assertIs(manager.translator(), translator)
        self.assertEqual(self._app.requested.count("app.locale"), 1)

    def testFallbackLocaleResolvesTranslationsFromAnotherLocale(self) -> None:
        """
        Wire the configured fallback locale into the translator.

        Validates that missing lines are resolved from the fallback
        declared in the configuration.
        """
        manager = self._makeManager({
            "app.locale": "es",
            "app.fallback_locale": "en",
        })
        translator = manager.translator()
        translator.setLocale("fr")
        self.assertEqual(translator.get("Welcome"), "Welcome")

    def testRejectsAMalformedConfiguredLocale(self) -> None:
        """
        Reject a malformed locale declared in the configuration.

        Validates that invalid settings fail fast instead of reaching
        the file system.
        """
        manager = self._makeManager({"app.locale": "../etc"})
        with self.assertRaises(InvalidLocaleException):
            manager.translator()

class TestLocalizationManagerDefaults(_ManagerFixture):
    """Validate the fallback values applied to missing settings."""

    def testDefaultsToEnglishWhenNoLocaleIsConfigured(self) -> None:
        """
        Default the active locale to English.

        Validates the documented default applied when ``app.locale`` is
        absent.
        """
        manager = self._makeManager({})
        self.assertEqual(manager.translator().getLocale(), "en")

    def testDefaultsTheFallbackToTheActiveLocale(self) -> None:
        """
        Default the fallback locale to the active locale.

        Validates that an incomplete configuration never falls back to
        an unrelated language.
        """
        manager = self._makeManager({"app.locale": "es"})
        translator = manager.translator()
        translator.setLocale("fr")
        self.assertEqual(translator.get("Welcome"), "Bienvenido")

    def testDefaultsTheLanguagePathToTheResourcesDirectory(self) -> None:
        """
        Default the language path to ``resources/lang``.

        Validates the convention applied when ``app.language_path`` is
        absent.
        """
        manager = self._makeManager({"app.locale": "es"})
        self.assertEqual(manager.translator().get("Welcome"), "Bienvenido")

class TestLocalizationManagerPaths(_ManagerFixture):
    """Validate resolution of the configured language directory."""

    def testResolvesRelativePathsAgainstTheApplicationRoot(self) -> None:
        """
        Anchor a relative language path to the application root.

        Validates that the manager never depends on the current working
        directory.
        """
        self._writeSource(self._base / "custom" / "lang", "es", "Relativo")
        manager = self._makeManager({
            "app.locale": "es",
            "app.language_path": "custom/lang",
        })
        self.assertEqual(manager.translator().get("Welcome"), "Relativo")

    def testHonoursAnAbsoluteLanguagePath(self) -> None:
        """
        Use an absolute language path verbatim.

        Validates that deployments pointing outside the project tree
        are supported.
        """
        absolute = self._base / "absolute" / "lang"
        self._writeSource(absolute, "es", "Absoluto")
        manager = self._makeManager({
            "app.locale": "es",
            "app.language_path": str(absolute),
        })
        self.assertEqual(manager.translator().get("Welcome"), "Absoluto")
