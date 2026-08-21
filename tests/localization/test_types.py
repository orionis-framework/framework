from collections.abc import Callable
from typing import TypeAliasType
from orionis.localization import types as types_module
from orionis.localization.types import LocaleCache, MissingKeyHandler, TranslationMap
from orionis.test import TestCase

# Type aliases published by the localization type module.
_EXPECTED_ALIASES: tuple[str, ...] = (
    "LocaleCache",
    "MissingKeyHandler",
    "TranslationMap",
)

class TestLocalizationTypeAliases(TestCase):
    """Validate the PEP 695 aliases used across the component."""

    def testModulePublishesEveryAlias(self) -> None:
        """
        Publish the three documented type aliases.

        Validates that no alias is renamed or removed without updating
        the consumers that annotate against them.
        """
        for name in _EXPECTED_ALIASES:
            self.assertIsInstance(getattr(types_module, name), TypeAliasType, name)

    def testTranslationMapDescribesAFlatStringMapping(self) -> None:
        """
        Describe a translation map as a flat string mapping.

        Validates that loaders and repositories agree on the shape of a
        resolved locale.
        """
        self.assertEqual(TranslationMap.__value__, dict[str, str])

    def testLocaleCacheIndexesTranslationMapsByLocale(self) -> None:
        """
        Describe the cache as translation maps keyed by locale.

        Validates that the repository cache reuses the translation map
        alias instead of duplicating its definition.
        """
        self.assertEqual(LocaleCache.__value__, dict[str, TranslationMap])

    def testMissingKeyHandlerIsResolvableAtRuntime(self) -> None:
        """
        Resolve the missing-key handler alias at runtime.

        Validates that introspection tools can evaluate the alias, which
        requires Callable to be imported outside a type-checking block.
        """
        self.assertEqual(
            MissingKeyHandler.__value__,
            Callable[[str, str], str | None],
        )
