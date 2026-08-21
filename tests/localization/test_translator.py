import tempfile
from pathlib import Path
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.exceptions import InvalidLocaleException
from orionis.localization.loader import TranslationLoader
from orionis.localization.repository import TranslationRepository
from orionis.localization.translator import Translator
from orionis.test import TestCase

# Spanish fixture acting as the active locale.
_SPANISH_SOURCE = (
    '{"Welcome": "Bienvenido", "Hello :name": "Hola :name", '
    '"Shared": "Compartido"}'
)

# English fixture acting as the fallback locale.
_ENGLISH_SOURCE = (
    '{"Welcome": "Welcome", "Only English": "Only English", '
    '"Shared": "Shared"}'
)

class _MissingRecorder:
    """Missing-key handler double recording every invocation."""

    __slots__ = ("calls", "line")

    def __init__(self, line: str | None) -> None:
        self.line = line
        self.calls: list[tuple[str, str]] = []

    def __call__(self, key: str, locale: str) -> str | None:
        """
        Record the missing key and return the configured line.

        Parameters
        ----------
        key : str
            Translation key that produced no match.
        locale : str
            Locale in which the key was requested.

        Returns
        -------
        str | None
            Configured replacement line, or None to echo the key.
        """
        self.calls.append((key, locale))
        return self.line

class _TranslatorFixture(TestCase):
    """Provide a translator wired to isolated translation sources."""

    def setUp(self) -> None:
        """
        Build a translator over a temporary language directory.

        Guarantees that every test observes its own translation sources
        and its own cache.

        Returns
        -------
        None
        """
        self._temporary = tempfile.TemporaryDirectory()
        self._root = Path(self._temporary.name)
        self._writeSource("es.json", _SPANISH_SOURCE)
        self._writeSource("en.json", _ENGLISH_SOURCE)
        self._loader = TranslationLoader(self._root)
        self._repository = TranslationRepository(self._loader)
        self._translator = self._makeTranslator()

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

    def _writeSource(self, name: str, payload: str) -> None:
        """
        Write or overwrite one of the fixture translation files.

        Parameters
        ----------
        name : str
            File name relative to the language directory.
        payload : str
            Raw JSON text stored with UTF-8 encoding.

        Returns
        -------
        None
        """
        (self._root / name).write_text(payload, encoding="utf-8")

    def _makeTranslator(self, locale: str = "es", fallback: str = "en") -> Translator:
        """
        Build a translator bound to the fixture collaborators.

        Parameters
        ----------
        locale : str
            Active locale of the translator.
        fallback : str
            Locale used when a translation is missing.

        Returns
        -------
        Translator
            Translator sharing the fixture loader and repository.
        """
        return Translator(
            locale=locale,
            fallback=fallback,
            loader=self._loader,
            repository=self._repository,
        )

class TestTranslatorDefinition(_TranslatorFixture):
    """Validate the structural contract of the translator."""

    def testImplementsTheTranslatorContract(self) -> None:
        """
        Implement the declared translator contract.

        Validates that the translator can be injected wherever the
        contract is required.
        """
        self.assertIsInstance(self._translator, ITranslator)

    def testInstancesDoNotCarryAnInstanceDictionary(self) -> None:
        """
        Keep translator instances free of an instance dictionary.

        Validates that the declared slots are effective, which requires
        the contract to declare empty slots as well.
        """
        self.assertFalse(hasattr(self._translator, "__dict__"))

    def testConstructorRejectsAMalformedActiveLocale(self) -> None:
        """
        Reject a malformed active locale at construction time.

        Validates that the translator is the single boundary enforcing
        safe locale codes.
        """
        with self.assertRaises(InvalidLocaleException):
            self._makeTranslator(locale="../etc")

    def testConstructorRejectsAMalformedFallbackLocale(self) -> None:
        """
        Reject a malformed fallback locale at construction time.

        Validates that the fallback code is validated with the same
        rules as the active locale.
        """
        with self.assertRaises(InvalidLocaleException):
            self._makeTranslator(fallback="en/../es")

class TestTranslatorLookup(_TranslatorFixture):
    """Validate translation resolution and fallback chaining."""

    def testResolvesLinesFromTheActiveLocale(self) -> None:
        """
        Resolve a line from the active locale.

        Validates the primary lookup performed before any fallback.
        """
        self.assertEqual(self._translator.get("Welcome"), "Bienvenido")

    def testExplicitLocaleOverridesTheActiveOne(self) -> None:
        """
        Resolve a line from an explicitly requested locale.

        Validates per-call locale selection without mutating the
        translator state.
        """
        self.assertEqual(self._translator.get("Welcome", locale="en"), "Welcome")
        self.assertEqual(self._translator.getLocale(), "es")

    def testFallsBackToTheFallbackLocale(self) -> None:
        """
        Resolve a missing line from the fallback locale.

        Validates the second stage of the documented lookup order.
        """
        self.assertEqual(self._translator.get("Only English"), "Only English")

    def testEchoesTheKeyWhenNoTranslationExists(self) -> None:
        """
        Return the key itself when no translation exists.

        Validates the final stage of the lookup order, which keeps
        templates readable while translations are missing.
        """
        self.assertEqual(self._translator.get("Unknown Key"), "Unknown Key")

    def testSkipsTheFallbackWhenItIsTheRequestedLocale(self) -> None:
        """
        Avoid a second lookup when the target is the fallback locale.

        Validates that the fallback stage is skipped when it would
        repeat the primary lookup.
        """
        self.assertEqual(self._translator.get("Ghost", locale="en"), "Ghost")

    def testRejectsAMalformedExplicitLocale(self) -> None:
        """
        Reject a malformed locale requested per call.

        Validates that untrusted locale codes never reach the loader.
        """
        with self.assertRaises(InvalidLocaleException):
            self._translator.get("Welcome", locale="")

class TestTranslatorExistence(_TranslatorFixture):
    """Validate existence checks over the translation maps."""

    def testFindsKeysDeclaredInTheActiveLocale(self) -> None:
        """
        Report a key declared in the active locale.

        Validates the primary existence check.
        """
        self.assertTrue(self._translator.has("Welcome"))

    def testFindsKeysDeclaredOnlyInTheFallbackLocale(self) -> None:
        """
        Report a key declared only in the fallback locale.

        Validates that the fallback locale participates in the check by
        default.
        """
        self.assertTrue(self._translator.has("Only English"))

    def testIgnoresTheFallbackWhenDisabled(self) -> None:
        """
        Ignore the fallback locale when explicitly disabled.

        Validates the strict mode used to detect untranslated lines.
        """
        self.assertFalse(self._translator.has("Only English", fallback=False))

    def testReturnsFalseWhenTheTargetIsTheFallbackLocale(self) -> None:
        """
        Avoid a redundant check when the target is the fallback.

        Validates that a missing key in the fallback locale is reported
        as absent without a second lookup.
        """
        self.assertFalse(self._translator.has("Unknown Key", locale="en"))

    def testReturnsFalseForUnknownKeys(self) -> None:
        """
        Report an unknown key as absent.

        Validates the negative case of the existence check.
        """
        self.assertFalse(self._translator.has("Unknown Key"))

    def testRejectsAMalformedExplicitLocale(self) -> None:
        """
        Reject a malformed locale requested per call.

        Validates that existence checks enforce the same locale rules
        as translation lookups.
        """
        with self.assertRaises(InvalidLocaleException):
            self._translator.has("Welcome", locale="es!")

class TestTranslatorReplacements(_TranslatorFixture):
    """Validate placeholder interpolation on resolved lines."""

    def testSubstitutesLowercasePlaceholders(self) -> None:
        """
        Substitute the raw placeholder variant.

        Validates the base case of parameter interpolation.
        """
        self.assertEqual(
            self._translator.get("Hello :name", name="Carlos"),
            "Hola Carlos",
        )

    def testSubstitutesCapitalizedAndUppercasedVariants(self) -> None:
        """
        Substitute the capitalized and uppercased variants.

        Validates that a single parameter feeds the three documented
        placeholder casings.
        """
        line = ":name | :Name | :NAME"
        self.assertEqual(
            self._translator.get(line, name="carlos"),
            "carlos | Carlos | CARLOS",
        )

    def testLongerParameterNamesAreAppliedFirst(self) -> None:
        """
        Apply longer parameter names before shorter ones.

        Validates that a short name never shadows a longer placeholder
        sharing its prefix.
        """
        line = ":name greets :name_full"
        self.assertEqual(
            self._translator.get(line, name="Ana", name_full="Ana Ruiz"),
            "Ana greets Ana Ruiz",
        )

    def testCoercesNonStringReplacementValues(self) -> None:
        """
        Coerce non-string replacement values into text.

        Validates that numeric parameters can be interpolated without
        an explicit conversion by the caller.
        """
        self.assertEqual(self._translator.get("Total: :total", total=7), "Total: 7")

    def testLeavesTheLineUntouchedWithoutParameters(self) -> None:
        """
        Skip interpolation when no parameter is provided.

        Validates the fast path that avoids scanning lines without
        placeholders.
        """
        self.assertEqual(self._translator.get("Hello :name"), "Hola :name")

class TestTranslatorMissingHandler(_TranslatorFixture):
    """Validate the hook invoked when a key cannot be resolved."""

    def testHandlerSuppliesTheResolvedLine(self) -> None:
        """
        Use the line returned by the missing-key handler.

        Validates that the hook can replace the default key echo.
        """
        self._translator.missing(_MissingRecorder("Sin traduccion"))
        self.assertEqual(self._translator.get("Ghost"), "Sin traduccion")

    def testHandlerReceivesTheKeyAndTheTargetLocale(self) -> None:
        """
        Pass the key and the target locale to the handler.

        Validates the payload reporting tools rely on to collect
        untranslated lines.
        """
        recorder = _MissingRecorder("x")
        self._translator.missing(recorder)
        self._translator.get("Ghost", locale="en")
        self.assertEqual(recorder.calls, [("Ghost", "en")])

    def testHandlerReturningNoLineFallsBackToTheKey(self) -> None:
        """
        Echo the key when the handler returns no line.

        Validates that a reporting-only handler does not break the
        rendered output.
        """
        self._translator.missing(_MissingRecorder(None))
        self.assertEqual(self._translator.get("Ghost"), "Ghost")

    def testHandlerCanBeRemoved(self) -> None:
        """
        Restore the default behaviour when the handler is removed.

        Validates that passing None detaches a previously registered
        hook.
        """
        self._translator.missing(_MissingRecorder("Sin traduccion"))
        self._translator.missing(None)
        self.assertEqual(self._translator.get("Ghost"), "Ghost")

class TestTranslatorPluralization(_TranslatorFixture):
    """Validate segment selection for pluralized lines."""

    def testSelectsTheSingularSegmentForOne(self) -> None:
        """
        Select the first segment for a count of one.

        Validates the positional rule applied without explicit
        conditions.
        """
        line = "Una manzana|:count manzanas"
        self.assertEqual(self._translator.choice(line, 1), "Una manzana")

    def testSelectsThePluralSegmentForOtherCounts(self) -> None:
        """
        Select the second segment for any other count.

        Validates the plural branch of the positional rule.
        """
        line = "Una manzana|:count manzanas"
        self.assertEqual(self._translator.choice(line, 5), "5 manzanas")

    def testReusesTheSingleSegmentForEveryCount(self) -> None:
        """
        Reuse the only segment when no plural form exists.

        Validates that a line without separators is always usable.
        """
        self.assertEqual(self._translator.choice("Sin plural", 9), "Sin plural")

    def testMatchesExactConditions(self) -> None:
        """
        Select the segment whose exact condition matches the count.

        Validates the ``{n}`` syntax, which takes precedence over the
        positional rule.
        """
        line = "{0} ninguna|{1} una manzana|[2,*] :count manzanas"
        self.assertEqual(self._translator.choice(line, 0), "ninguna")
        self.assertEqual(self._translator.choice(line, 1), "una manzana")
        self.assertEqual(self._translator.choice(line, 7), "7 manzanas")

    def testMatchesTheWildcardExactCondition(self) -> None:
        """
        Select the segment declaring a wildcard exact condition.

        Validates the catch-all ``{*}`` form.
        """
        line = "{*} cualquiera|otra"
        self.assertEqual(self._translator.choice(line, 42), "cualquiera")

    def testMatchesBoundedRanges(self) -> None:
        """
        Select the segment whose bounded range contains the count.

        Validates that both bounds of a range are evaluated.
        """
        line = "[0,1] pocas|[2,4] varias|[5,*] muchas"
        self.assertEqual(self._translator.choice(line, 1), "pocas")
        self.assertEqual(self._translator.choice(line, 3), "varias")
        self.assertEqual(self._translator.choice(line, 9), "muchas")

    def testIgnoresNonNumericExactConditions(self) -> None:
        """
        Fall back to the positional rule for invalid exact conditions.

        Validates that a malformed condition never selects a segment by
        accident.
        """
        line = "{x} primera|segunda"
        self.assertEqual(self._translator.choice(line, 1), "primera")
        self.assertEqual(self._translator.choice(line, 2), "segunda")

    def testIgnoresNonNumericRangeBounds(self) -> None:
        """
        Fall back to the positional rule for invalid range bounds.

        Validates that a malformed bound is treated as a failed match
        instead of an error.
        """
        line = "[a,*] primera|segunda"
        self.assertEqual(self._translator.choice(line, 5), "segunda")

    def testInjectsTheCountPlaceholderAutomatically(self) -> None:
        """
        Expose the count under the ``:count`` placeholder.

        Validates that pluralized lines can render the quantity without
        an explicit parameter.
        """
        self.assertEqual(
            self._translator.choice("Hay :count manzanas", 3),
            "Hay 3 manzanas",
        )

    def testSubstitutesAdditionalParameters(self) -> None:
        """
        Interpolate extra parameters into the selected segment.

        Validates that pluralization and interpolation compose.
        """
        line = "Una manzana de :owner|:count manzanas de :owner"
        self.assertEqual(
            self._translator.choice(line, 2, owner="Ana"),
            "2 manzanas de Ana",
        )

    def testResolvesTheLineFromTheRequestedLocale(self) -> None:
        """
        Resolve the pluralized line from an explicit locale.

        Validates that pluralization honours per-call locale selection.
        """
        self._writeSource("en.json", '{"apples": "one apple|:count apples"}')
        self._repository.flush()
        self.assertEqual(
            self._translator.choice("apples", 4, locale="en"),
            "4 apples",
        )

class TestTranslatorLocaleManagement(_TranslatorFixture):
    """Validate runtime locale switching and discovery."""

    def testReportsTheActiveLocale(self) -> None:
        """
        Report the locale currently in use.

        Validates the accessor consumed by the template globals.
        """
        self.assertEqual(self._translator.getLocale(), "es")

    def testSwitchesTheActiveLocaleAtRuntime(self) -> None:
        """
        Apply a new active locale immediately.

        Validates that subsequent lookups use the newly selected
        locale.
        """
        self._translator.setLocale("en")
        self.assertEqual(self._translator.getLocale(), "en")
        self.assertEqual(self._translator.get("Welcome"), "Welcome")

    def testRejectsMalformedLocaleCodes(self) -> None:
        """
        Reject locale codes that are unsafe for path resolution.

        Validates the anti-traversal guard enforced at this boundary.
        """
        for candidate in ("", "../etc", "es/es", "es.json", "es ", "_es"):
            with self.assertRaises(InvalidLocaleException):
                self._translator.setLocale(candidate)

    def testRejectsLocaleCodesThatAreNotStrings(self) -> None:
        """
        Reject a locale code that is not a string.

        Validates that the guard runs before any regular expression
        matching.
        """
        with self.assertRaises(InvalidLocaleException):
            self._translator.setLocale(42)  # type: ignore[arg-type]

    def testAcceptsRegionAndScriptSubtags(self) -> None:
        """
        Accept locale codes carrying region or script subtags.

        Validates that the guard does not reject legitimate BCP 47
        style codes.
        """
        for candidate in ("en", "en_US", "en-US", "zh-Hant-TW"):
            self._translator.setLocale(candidate)
            self.assertEqual(self._translator.getLocale(), candidate)

    def testDiscoversTheAvailableLocales(self) -> None:
        """
        Expose the locales discovered by the loader.

        Validates the delegation used by the template globals to render
        language switchers.
        """
        self.assertEqual(self._translator.availableLocales(), ("en", "es"))

class TestTranslatorCacheManagement(_TranslatorFixture):
    """Validate cache invalidation exposed by the translator."""

    def testReloadOfASingleLocalePicksUpFileChanges(self) -> None:
        """
        Re-read one locale after invalidating it.

        Validates the targeted invalidation used when a single language
        file changes.
        """
        self.assertEqual(self._translator.get("Welcome"), "Bienvenido")
        self._writeSource("es.json", '{"Welcome": "Hola de nuevo"}')
        self._translator.reload("es")
        self.assertEqual(self._translator.get("Welcome"), "Hola de nuevo")

    def testReloadWithoutLocaleDiscardsEveryLocale(self) -> None:
        """
        Re-read every locale when no locale is supplied.

        Validates the bulk invalidation used after a deployment.
        """
        self._translator.get("Welcome")
        self._translator.get("Welcome", locale="en")
        self._writeSource("es.json", '{"Welcome": "Nuevo"}')
        self._writeSource("en.json", '{"Welcome": "New"}')
        self._translator.reload()
        self.assertEqual(self._translator.get("Welcome"), "Nuevo")
        self.assertEqual(self._translator.get("Welcome", locale="en"), "New")

    def testReloadRejectsMalformedLocales(self) -> None:
        """
        Reject a malformed locale on targeted invalidation.

        Validates that cache management enforces the same locale rules
        as lookups.
        """
        with self.assertRaises(InvalidLocaleException):
            self._translator.reload("../etc")

    def testForgetReportsWhetherAnEntryWasRemoved(self) -> None:
        """
        Report whether the invalidated locale was cached.

        Validates the boolean contract used to detect a no-op
        invalidation.
        """
        self._translator.get("Welcome")
        self.assertTrue(self._translator.forget("es"))
        self.assertFalse(self._translator.forget("es"))

    def testForgetRejectsMalformedLocales(self) -> None:
        """
        Reject a malformed locale when discarding a cache entry.

        Validates that the guard also protects the eviction path.
        """
        with self.assertRaises(InvalidLocaleException):
            self._translator.forget("es/es")

    def testFlushDiscardsEveryCachedLocale(self) -> None:
        """
        Discard every cached locale in a single call.

        Validates the shortcut exposed for full cache invalidation.
        """
        self._translator.get("Welcome")
        self._translator.flush()
        self.assertEqual(self._repository.loadedLocales(), ())
