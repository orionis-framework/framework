from orionis.foundation.application import Application
from orionis.support.facades.lang import Lang
from orionis.test import TestCase
from orionis.view.contracts.environment import IViewEnvironment

class TestLangFacadeIntegration(TestCase):
    """Validate the Lang facade against the booted application."""

    def testResolvesLinesFromTheShippedResourceFiles(self) -> None:
        """
        Resolve lines from the real resources/lang files.

        Validates the wiring between the provider, the manager, and the
        translation sources of the application.
        """
        self.assertEqual(Lang.get("Welcome", locale="es"), "Bienvenido")
        self.assertEqual(Lang.get("Welcome", locale="en"), "Welcome")

    def testSubstitutesParametersOnResolvedLines(self) -> None:
        """
        Substitute placeholders on the resolved line.

        Validates that interpolation also applies to keys echoed back
        because no translation is registered for them.
        """
        self.assertEqual(
            Lang.get("Hello :name", locale="es", name="Carlos"),
            "Hello Carlos",
        )

    def testEchoesKeysWithoutTranslation(self) -> None:
        """
        Return the key itself for unknown translations.

        Validates that the facade never raises on a missing line.
        """
        self.assertEqual(Lang.get("Unknown Key"), "Unknown Key")

    def testPluralizesThroughTheChoiceMethod(self) -> None:
        """
        Select singular and plural segments through the facade.

        Validates that pluralization is reachable from application
        code without resolving the contract manually.
        """
        line = "There is one apple|There are :count apples"
        self.assertEqual(Lang.choice(line, 1), "There is one apple")
        self.assertEqual(Lang.choice(line, 5), "There are 5 apples")

    def testSwitchesTheActiveLocaleAtRuntime(self) -> None:
        """
        Switch the active locale and restore it afterwards.

        Validates that the facade exposes a single shared translator
        whose locale can be changed at runtime.
        """
        original = Lang.getLocale()
        try:
            Lang.setLocale("es")
            self.assertEqual(Lang.getLocale(), "es")
            self.assertEqual(Lang.get("Welcome"), "Bienvenido")
        finally:
            Lang.setLocale(original)
        self.assertEqual(Lang.getLocale(), original)

    def testDiscoversTheConfiguredLocales(self) -> None:
        """
        List the locales shipped with the application.

        Validates that discovery reflects the real resources/lang
        directory.
        """
        locales = Lang.availableLocales()
        self.assertIn("en", locales)
        self.assertIn("es", locales)

class TestTranslationTemplateIntegration(TestCase):
    """Validate the translation globals inside real Jinja2 templates."""

    async def _render(self, source: str) -> str:
        """
        Render a template string through the application view engine.

        Parameters
        ----------
        source : str
            Jinja2 template source to compile and render.

        Returns
        -------
        str
            Rendered template output.
        """
        app = Application()
        environment: IViewEnvironment = await app.make(IViewEnvironment)
        template = environment.getJinjaEnvironment().from_string(source)
        return await template.render_async()

    async def testDunderGlobalTranslatesInsideTemplates(self) -> None:
        """
        Resolve translations through the __ template global.

        Validates the shortest alias published for view templates.
        """
        rendered = await self._render('{{ __("Welcome", locale="es") }}')
        self.assertEqual(rendered, "Bienvenido")

    async def testTransGlobalSubstitutesParameters(self) -> None:
        """
        Substitute placeholders through the trans template global.

        Validates that view parameters reach the translator untouched.
        """
        rendered = await self._render(
            '{{ trans("Hello :name", locale="es", name="Ana") }}',
        )
        self.assertEqual(rendered, "Hello Ana")

    async def testChoiceGlobalPluralizesInsideTemplates(self) -> None:
        """
        Pluralize a line through the choice template global.

        Validates that quantity-aware lines can be rendered without
        controller support.
        """
        rendered = await self._render(
            '{{ choice("There is one apple|There are :count apples", 3) }}',
        )
        self.assertEqual(rendered, "There are 3 apples")

    async def testLocaleGlobalExposesTheActiveLocale(self) -> None:
        """
        Expose the active locale through the locale global.

        Validates the value used to render the language attribute of
        the document.
        """
        rendered = await self._render('<html lang="{{ locale() }}">')
        self.assertEqual(rendered, f'<html lang="{Lang.getLocale()}">')

    async def testLocalesGlobalListsEveryAvailableLocale(self) -> None:
        """
        List every available locale through the locales global.

        Validates the data backing language switchers rendered in
        templates.
        """
        rendered = await self._render('{{ locales()|join(",") }}')
        for locale in ("en", "es"):
            self.assertIn(locale, rendered)

    async def testRuntimeLocaleSwitchIsVisibleInTemplates(self) -> None:
        """
        Reflect a runtime locale switch on the next render.

        Validates that templates always read the current state of the
        shared translator.
        """
        original = Lang.getLocale()
        try:
            Lang.setLocale("es")
            rendered = await self._render('{{ __("Welcome") }}|{{ locale() }}')
            self.assertEqual(rendered, "Bienvenido|es")
        finally:
            Lang.setLocale(original)
