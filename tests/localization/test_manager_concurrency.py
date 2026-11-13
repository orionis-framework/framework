# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect lazy localization initialization across concurrent callers."""

import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from threading import Barrier, BrokenBarrierError
from types import SimpleNamespace
from unittest.mock import patch

from orionis.localization.contracts.translator import ITranslator
from orionis.localization.manager import LocalizationManager
from orionis.test import TestCase


class TestLocalizationManagerConcurrency(TestCase):
    """Check that every concurrent caller receives one shared translator."""

    def testPublishesOneTranslatorDuringConcurrentInitialization(self) -> None:
        """Return one instance when two threads request the cold manager."""
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        configuration = {
            "app.locale": "en",
            "app.fallback_locale": "en",
            "app.language_path": str(directory),
        }
        application = SimpleNamespace(basePath=directory, config=configuration.get)
        manager = LocalizationManager(application)
        builders = Barrier(2)
        original_build = LocalizationManager._LocalizationManager__buildTranslator

        def build_together(instance: LocalizationManager) -> ITranslator:
            """Coordinate competing builders while allowing serialized construction.

            Parameters
            ----------
            instance : LocalizationManager
                Manager whose real translator must be constructed.

            Returns
            -------
            ITranslator
                Translator produced by the real factory.
            """
            # A serialized factory has one builder, so the barrier expires.
            with suppress(BrokenBarrierError):
                builders.wait(timeout=5)
            return original_build(instance)

        with (
            patch.object(
                LocalizationManager,
                "_LocalizationManager__buildTranslator",
                new=build_together,
            ),
            ThreadPoolExecutor(max_workers=2) as workers,
        ):
            futures = [workers.submit(manager.translator) for _ in range(2)]
            first, second = (future.result(timeout=10) for future in futures)
        self.assertIs(first, second)
        self.assertIsInstance(first, ITranslator)
        self.assertIs(manager.translator(), first)
