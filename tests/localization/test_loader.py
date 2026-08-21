import tempfile
from pathlib import Path
from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.exceptions import (
    TranslationFileNotFoundException,
    TranslationSyntaxException,
)
from orionis.localization.loader import TranslationLoader
from orionis.test import TestCase

def write_source(path: Path, payload: str) -> None:
    """
    Write a raw translation payload to disk.

    Parameters
    ----------
    path : Path
        Destination file; missing parent directories are created.
    payload : str
        Raw JSON text stored with UTF-8 encoding.

    Returns
    -------
    None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")

class _LoaderFixture(TestCase):
    """Provide an isolated language directory for every test."""

    def setUp(self) -> None:
        """
        Create a temporary language directory.

        Guarantees that each test reads its own translation sources and
        never observes files written by another case.

        Returns
        -------
        None
        """
        self._temporary = tempfile.TemporaryDirectory()
        self._root = Path(self._temporary.name)
        self._loader = TranslationLoader(self._root)

    def tearDown(self) -> None:
        """
        Remove the temporary language directory.

        Guarantees that no fixture file survives the test that created
        it.

        Returns
        -------
        None
        """
        self._temporary.cleanup()

class TestTranslationLoaderDefinition(_LoaderFixture):
    """Validate the structural contract of the loader."""

    def testImplementsTheLoaderContract(self) -> None:
        """
        Implement the declared loader contract.

        Validates that the concrete loader can be injected wherever the
        contract is required.
        """
        self.assertIsInstance(self._loader, ITranslationLoader)

    def testInstancesDoNotCarryAnInstanceDictionary(self) -> None:
        """
        Keep loader instances free of an instance dictionary.

        Validates that the declared slots are effective, which requires
        the contract to declare empty slots as well.
        """
        self.assertFalse(hasattr(self._loader, "__dict__"))

class TestTranslationLoaderRootFiles(_LoaderFixture):
    """Validate decoding of the root JSON file of a locale."""

    def testLoadsLiteralSourceTextEntries(self) -> None:
        """
        Expose root JSON keys as literal source texts.

        Validates the Laravel-style convention where the key is the
        untranslated line itself.
        """
        write_source(self._root / "es.json", '{"Welcome": "Bienvenido"}')
        self.assertEqual(self._loader.load("es")["Welcome"], "Bienvenido")

    def testFlattensNestedObjectsDeclaredInTheRootFile(self) -> None:
        """
        Flatten nested root objects with dot notation.

        Validates that a grouped structure declared inline behaves like
        a grouped file.
        """
        write_source(
            self._root / "es.json",
            '{"messages": {"greet": "Hola", "deep": {"bye": "Adios"}}}',
        )
        loaded = self._loader.load("es")
        self.assertEqual(loaded["messages.greet"], "Hola")
        self.assertEqual(loaded["messages.deep.bye"], "Adios")

    def testCoercesNonStringRootValuesToText(self) -> None:
        """
        Coerce non-string root values into text.

        Validates that numeric or boolean payloads never leak a
        non-string value into the translation map.
        """
        write_source(self._root / "es.json", '{"Total": 5, "Ready": true}')
        loaded = self._loader.load("es")
        self.assertEqual(loaded["Total"], "5")
        self.assertEqual(loaded["Ready"], "True")

    def testDecodesUtf8EncodedSources(self) -> None:
        """
        Decode translation sources as UTF-8 text.

        Validates that accented and non-Latin characters survive the
        decoding step untouched.
        """
        write_source(
            self._root / "es.json",
            '{"Goodbye": "Adi\u00f3s", "Welcome": "\u3088\u3046\u3053\u305d"}',
        )
        loaded = self._loader.load("es")
        self.assertEqual(loaded["Goodbye"], "Adi\u00f3s")
        self.assertEqual(loaded["Welcome"], "\u3088\u3046\u3053\u305d")

class TestTranslationLoaderGroupedFiles(_LoaderFixture):
    """Validate decoding of the grouped files of a locale."""

    def testFlattensGroupedFilesWithDotNotation(self) -> None:
        """
        Prefix grouped entries with the file stem.

        Validates the ``group.key`` convention used by grouped
        translation files.
        """
        write_source(
            self._root / "es" / "validation.json",
            '{"required": "El campo es obligatorio"}',
        )
        loaded = self._loader.load("es")
        self.assertEqual(loaded["validation.required"], "El campo es obligatorio")

    def testFlattensNestedGroupedObjects(self) -> None:
        """
        Flatten nested grouped objects recursively.

        Validates that arbitrarily deep structures collapse into a
        single flat mapping.
        """
        write_source(
            self._root / "es" / "validation.json",
            '{"nested": {"email": "Correo invalido"}}',
        )
        self.assertEqual(
            self._loader.load("es")["validation.nested.email"],
            "Correo invalido",
        )

    def testCoercesNonStringGroupedValuesToText(self) -> None:
        """
        Coerce non-string grouped values into text.

        Validates that the flattening routine normalizes every leaf to
        a string.
        """
        write_source(self._root / "es" / "limits.json", '{"max": 10}')
        self.assertEqual(self._loader.load("es")["limits.max"], "10")

    def testMergesEveryGroupedFileOfTheLocale(self) -> None:
        """
        Merge all grouped files belonging to the locale.

        Validates that translations are not restricted to a single
        group per locale.
        """
        write_source(self._root / "es" / "auth.json", '{"failed": "Fallo"}')
        write_source(self._root / "es" / "passwords.json", '{"reset": "Listo"}')
        loaded = self._loader.load("es")
        self.assertEqual(loaded["auth.failed"], "Fallo")
        self.assertEqual(loaded["passwords.reset"], "Listo")

    def testRootEntriesOverrideGroupedEntries(self) -> None:
        """
        Give precedence to the root file on key collision.

        Validates the documented merge order where literal-text entries
        win over grouped entries.
        """
        write_source(self._root / "es" / "auth.json", '{"failed": "Grouped"}')
        write_source(self._root / "es.json", '{"auth.failed": "Root"}')
        self.assertEqual(self._loader.load("es")["auth.failed"], "Root")

class TestTranslationLoaderMissingSources(_LoaderFixture):
    """Validate the behaviour when translation sources are absent."""

    def testUnknownLocaleYieldsAnEmptyMap(self) -> None:
        """
        Return an empty map for a locale without sources.

        Validates that a missing locale is not an error but an empty
        translation map.
        """
        self.assertEqual(self._loader.load("fr"), {})

    def testGroupedDirectoryWithoutJsonFilesIsIgnored(self) -> None:
        """
        Ignore a grouped directory holding no JSON file.

        Validates that unrelated directories never break the load
        sequence.
        """
        (self._root / "es").mkdir()
        write_source(self._root / "es" / "notes.txt", "ignored")
        self.assertEqual(self._loader.load("es"), {})

class TestTranslationLoaderInvalidSources(_LoaderFixture):
    """Validate the errors raised for unusable translation files."""

    def testMalformedJsonRaisesSyntaxException(self) -> None:
        """
        Reject a translation file holding malformed JSON.

        Validates that decoding failures surface as a localization
        error instead of a msgspec error.
        """
        write_source(self._root / "es.json", "{broken")
        with self.assertRaises(TranslationSyntaxException):
            self._loader.load("es")

    def testNonObjectRootFileRaisesSyntaxException(self) -> None:
        """
        Reject a root file whose payload is not an object.

        Validates that only JSON objects are accepted as translation
        sources.
        """
        write_source(self._root / "es.json", '["Bienvenido"]')
        with self.assertRaises(TranslationSyntaxException):
            self._loader.load("es")

    def testNonObjectGroupedFileRaisesSyntaxException(self) -> None:
        """
        Reject a grouped file whose payload is not an object.

        Validates that the object requirement applies to grouped files
        as well.
        """
        write_source(self._root / "es" / "auth.json", '"Fallo"')
        with self.assertRaises(TranslationSyntaxException):
            self._loader.load("es")

    def testNonUtf8FileRaisesSyntaxException(self) -> None:
        """
        Reject a translation file stored in another encoding.

        Validates that a decoding failure surfaces as a localization
        error instead of a bare UnicodeDecodeError.
        """
        (self._root / "es.json").write_bytes(
            '{"Goodbye": "Adi\u00f3s"}'.encode("latin-1"),
        )
        with self.assertRaises(TranslationSyntaxException):
            self._loader.load("es")

    def testFileRemovedAfterDiscoveryRaisesNotFoundException(self) -> None:
        """
        Reject reading a file that vanished after discovery.

        Validates the race guard protecting the loader when a source is
        deleted between listing and reading.
        """
        with self.assertRaises(TranslationFileNotFoundException):
            self._loader._TranslationLoader__readFile(self._root / "ghost.json")

class TestTranslationLoaderDiscovery(_LoaderFixture):
    """Validate discovery of the locales available on disk."""

    def testDiscoversLocalesFromRootFilesAndDirectories(self) -> None:
        """
        Discover locales from root files and grouped directories.

        Validates that both source layouts contribute to the sorted
        list of available locales.
        """
        write_source(self._root / "es.json", "{}")
        write_source(self._root / "en.json", "{}")
        write_source(self._root / "fr" / "auth.json", "{}")
        self.assertEqual(self._loader.availableLocales(), ("en", "es", "fr"))

    def testIgnoresDirectoriesWithoutTranslationFiles(self) -> None:
        """
        Ignore directories that hold no JSON file.

        Validates that unrelated folders are never reported as
        available locales.
        """
        write_source(self._root / "es.json", "{}")
        (self._root / "cache").mkdir()
        self.assertEqual(self._loader.availableLocales(), ("es",))

    def testIgnoresFilesThatAreNotJson(self) -> None:
        """
        Ignore files whose extension is not JSON.

        Validates that documentation or backup files never become
        available locales.
        """
        write_source(self._root / "es.json", "{}")
        write_source(self._root / "readme.txt", "ignored")
        self.assertEqual(self._loader.availableLocales(), ("es",))

    def testReturnsNoLocalesWhenThePathIsMissing(self) -> None:
        """
        Report no locales when the language path does not exist.

        Validates that a missing directory degrades gracefully instead
        of raising an operating system error.
        """
        loader = TranslationLoader(self._root / "missing")
        self.assertEqual(loader.availableLocales(), ())
