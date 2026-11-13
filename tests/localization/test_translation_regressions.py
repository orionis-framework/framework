# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect literal replacement values from repeated interpolation."""

from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.localization import TranslationLoader, TranslationRepository, Translator
from orionis.test import TestCase


class TestTranslationRegressions(TestCase):
    """Exercise interpolation through the public translation methods."""

    def testReplacementValuesRemainLiteral(self) -> None:
        """Replace source placeholders once without interpreting inserted text."""
        with TemporaryDirectory() as directory:
            loader = TranslationLoader(Path(directory))
            translator = Translator(
                locale="en",
                fallback="en",
                loader=loader,
                repository=TranslationRepository(loader),
            )
            scenarios = (
                ("::long", {"long": "x", "x": "changed"}, ":x"),
                (":a:long", {"long": "x", "ax": "changed"}, ":ax"),
                ("::1", {"1": "1"}, ":1"),
                (":name :x", {"name": ":x", "x": "literal"}, ":x literal"),
                (":NAME :Name :name", {"name": ":Name"}, ":NAME :name :Name"),
                (
                    ":name_full :name",
                    {"name_full": ":name", "name": "Ada"},
                    ":name Ada",
                ),
            )
            for source, replacements, expected in scenarios:
                with self.subTest(source=source, replacements=replacements):
                    self.assertEqual(translator.get(source, **replacements), expected)
            self.assertEqual(
                translator.choice(
                    ":name_long|:name_long :count",
                    2,
                    name_long=":count",
                ),
                ":count 2",
            )
