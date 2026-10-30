from typing import Self
from unittest.mock import patch
from orionis.localization.repository import TranslationRepository
from orionis.test import TestCase
from tests.localization.test_repository import _RecordingLoader

class TestTranslationCacheLimits(TestCase):
    """Bound negative entries and allow translations to appear after a miss."""

    def testCapacityAndRecentLocales(self: Self) -> None:
        """
        Keep a hard bound after ten thousand distinct locale names.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        loader = _RecordingLoader({"es": {"hi": "hola"}})
        repository = TranslationRepository(loader, max_locales=16)
        for index in range(10000):
            repository.get(str(index))
            repository.get("es")
        self.assertEqual(len(repository.loadedLocales()), 16)
        self.assertTrue(repository.has("es"))
        self.assertLessEqual(len(repository._expires), 16)

    def testNegativeExpiryForgetAndFlush(self: Self) -> None:
        """
        Reload absent locales at TTL expiry and honor explicit invalidation.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        loader = _RecordingLoader({})
        repository = TranslationRepository(loader, negative_ttl=2)
        with patch("orionis.localization.repository.monotonic", return_value=1):
            self.assertEqual(repository.get("es"), {})
            loader.payloads["es"] = {"hi": "hola"}
            self.assertEqual(repository.get("es"), {})
        with patch("orionis.localization.repository.monotonic", return_value=4):
            self.assertEqual(repository.get("es"), {"hi": "hola"})
        self.assertTrue(repository.forget("es"))
        repository.flush()
        self.assertEqual(repository.loadedLocales(), ())
        self.assertEqual(repository._expires, {})
