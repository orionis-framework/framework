# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect translation loading boundaries and runtime constructor types."""

import os
import tempfile
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.exceptions import (
    InvalidLocaleException,
    TranslationException,
    TranslationFileNotFoundException,
)
from orionis.localization.loader import TranslationLoader
from orionis.localization.repository import TranslationRepository
from orionis.test import TestCase

if os.name == "nt":
    from _winapi import CreateJunction


class TestTranslationLoadingRegressions(TestCase):
    """Keep translation reads within the configured language directory."""

    def setUp(self) -> None:
        """Create independent language and external fixture directories."""
        super().setUp()
        self._directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self._root = self._directory / "lang"
        self._root.mkdir()
        self._loader = TranslationLoader(self._root)

    def testRejectsMalformedLocalesBeforeLoading(self) -> None:
        """Reject path components and trailing newlines at the loader boundary."""
        outside = self._directory / "outside.json"
        outside.write_text('{"message": "outside fixture"}', encoding="utf-8")
        for locale in (
            "",
            ".",
            "..",
            "../outside",
            "..\\outside",
            str(outside.with_suffix("")),
            "en\n",
            "en/GB",
            42,
        ):
            with self.subTest(locale=locale), self.assertRaises(InvalidLocaleException):
                self._loader.load(locale)

    def testRejectsLocaleDirectoriesLinkedOutsideTheRoot(self) -> None:
        """Reject external directory links during loading and omit discovery."""
        outside = self._directory / "external"
        outside.mkdir()
        (outside / "messages.json").write_text(
            '{"message": "outside fixture"}',
            encoding="utf-8",
        )
        linked = self._root / "en"
        if os.name == "nt":
            CreateJunction(str(outside), str(linked))
        else:
            linked.symlink_to(outside, target_is_directory=True)
        with self.subTest(operation="load"), self.assertRaises(TranslationException):
            self._loader.load("en")
        with self.subTest(operation="discovery"):
            self.assertEqual(self._loader.availableLocales(), ())

    def testResolvesConcreteConstructorAnnotations(self) -> None:
        """Resolve concrete dependency annotations used during injection."""
        for constructor, parameter, expected in (
            (TranslationLoader.__init__, "path", Path),
            (TranslationRepository.__init__, "loader", ITranslationLoader),
        ):
            with self.subTest(constructor=constructor.__qualname__):
                self.assertEqual(get_type_hints(constructor)[parameter], expected)

    def testPreservesMissingFileErrorsDuringRead(self) -> None:
        """Translate a source disappearing after discovery to the public error."""
        (self._root / "en.json").write_text("{}", encoding="utf-8")
        with (
            patch.object(Path, "read_bytes", side_effect=FileNotFoundError),
            self.assertRaises(TranslationFileNotFoundException),
        ):
            self._loader.load("en")
