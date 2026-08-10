from __future__ import annotations
from orionis.foundation.application import Application
from orionis.support.facades.lang import Lang
from orionis.test import TestCase
from orionis.view.contracts.environment import IViewEnvironment

class TestWebTranslationFacade(TestCase):
    """Validate the Lang facade against the booted application."""

    async def testFacadeTranslatesFromResourceFiles(self) -> None:
        """Lang resolves lines from the real resources/lang files."""
        self.assertEqual(Lang.get("Welcome", locale="es"), "Bienvenido")
        self.assertEqual(Lang.get("Welcome", locale="en"), "Welcome")

    async def testFacadeReplacesParameters(self) -> None:
        """Lang substitutes Laravel-style placeholders on the resolved line."""
        # Shipped lines declare no placeholders, so the key acts as the line.
        self.assertEqual(
            Lang.get("Hello :name", locale="es", name="Carlos"),
            "Hello Carlos",
        )
        self.assertEqual(
            Lang.get("Hello :name", locale="en", name="Carlos"),
            "Hello Carlos",
        )

    async def testFacadeReturnsKeyForMissingTranslations(self) -> None:
        """Unknown keys are echoed back unchanged."""
        self.assertEqual(Lang.get("Unknown Key"), "Unknown Key")

    async def testFacadePluralizesWithChoice(self) -> None:
        """Lang.choice selects singular and plural segments."""
        line = "There is one apple|There are :count apples"
        self.assertEqual(Lang.choice(line, 1), "There is one apple")
        self.assertEqual(Lang.choice(line, 5), "There are 5 apples")

    async def testFacadeSwitchesLocaleAtRuntime(self) -> None:
        """Switching the locale takes effect and can be restored."""
        original = Lang.getLocale()
        try:
            Lang.setLocale("es")
            self.assertEqual(Lang.getLocale(), "es")
            self.assertEqual(Lang.get("Welcome"), "Bienvenido")
        finally:
            Lang.setLocale(original)
        self.assertEqual(Lang.getLocale(), original)

    async def testFacadeDiscoversConfiguredLocales(self) -> None:
        """The available locales reflect the resources/lang directory."""
        locales = Lang.availableLocales()
        self.assertIn("en", locales)
        self.assertIn("es", locales)

class TestWebTranslationRendering(TestCase):
    """Validate the translation globals inside real Jinja2 templates."""

    async def __render(self, source: str) -> str:
        """
        Render a template string through the application view environment.

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

    async def testTemplateTranslatesWithDunderGlobal(self) -> None:
        """The __ global resolves translations inside templates."""
        rendered = await self.__render('{{ __("Welcome", locale="es") }}')
        self.assertEqual(rendered, "Bienvenido")

    async def testTemplateTranslatesWithTransGlobal(self) -> None:
        """The trans global substitutes placeholders inside templates."""
        rendered = await self.__render(
            '{{ trans("Hello :name", locale="es", name="Ana") }}',
        )
        self.assertEqual(rendered, "Hello Ana")

    async def testTemplatePluralizesWithChoiceGlobal(self) -> None:
        """The choice global pluralizes lines inside templates."""
        rendered = await self.__render(
            '{{ choice("There is one apple|There are :count apples", 3) }}',
        )
        self.assertEqual(rendered, "There are 3 apples")

    async def testTemplateExposesActiveLocale(self) -> None:
        """The locale global matches the translator active locale."""
        rendered = await self.__render('<html lang="{{ locale() }}">')
        self.assertEqual(rendered, f'<html lang="{Lang.getLocale()}">')

    async def testTemplateListsAvailableLocales(self) -> None:
        """The locales global lists every discovered locale."""
        rendered = await self.__render('{{ locales()|join(",") }}')
        for locale in ("en", "es"):
            self.assertIn(locale, rendered)

    async def testTemplateReflectsRuntimeLocaleSwitch(self) -> None:
        """Locale switches are visible in subsequent renders."""
        original = Lang.getLocale()
        try:
            Lang.setLocale("es")
            rendered = await self.__render('{{ __("Welcome") }}|{{ locale() }}')
            self.assertEqual(rendered, "Bienvenido|es")
        finally:
            Lang.setLocale(original)
