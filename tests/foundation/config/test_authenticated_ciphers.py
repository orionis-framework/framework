# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect authenticated encryption configuration before key generation."""

from dataclasses import fields
from inspect import signature
from types import SimpleNamespace
from unittest.mock import Mock, patch
from config.app import BootstrapApp
from orionis.console.commands.support.key_generate import KeyGenerateCommand
from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.foundation.config.app import App, Cipher
from orionis.test import TestCase


class TestAuthenticatedCipherConfiguration(TestCase):
    """Exercise core and generated application configuration without persistence."""

    def setUp(self) -> None:
        """Replace only environment access used by the application factories.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self.environment = Mock()
        self.environment.get.side_effect = lambda _name, default=None: default
        for module in (
            "orionis.foundation.config.app.entities.app",
            "config.app",
        ):
            self.enterContext(patch(module + ".Env", self.environment))

    def testDefaultCipherUsesAes256Gcm(self) -> None:
        """Default both application configuration factories to authenticated AES.

        Returns
        -------
        None
            No return value.
        """
        for factory in (App, BootstrapApp):
            with self.subTest(factory=factory.__name__):
                self.assertEqual(factory(key=b"k" * 32).cipher, "AES-256-GCM")
        self.assertEqual(
            next(field for field in fields(App) if field.name == "cipher").metadata[
                "default"
            ],
            "AES-256-GCM",
        )
        self.environment.set.assert_not_called()

    def testLegacyCbcFailsBeforeKeyGenerationOrPersistence(self) -> None:
        """Reject legacy names, values and enum members before changing keys.

        Returns
        -------
        None
            No return value.
        """
        with patch.object(SecureKeyGenerator, "generate") as generate:
            for factory in (App, BootstrapApp):
                for cipher in (Cipher.AES_128_CBC, Cipher.AES_256_CBC):
                    for value in (cipher, cipher.name.lower(), cipher.value.lower()):
                        for key in (None, b"k" * (16 if "128" in cipher.value else 32)):
                            with (
                                self.subTest(
                                    factory=factory.__name__,
                                    cipher=value,
                                    key=key,
                                ),
                                self.assertRaisesRegex(ValueError, "authenticated"),
                            ):
                                factory(cipher=value, key=key)
            generate.assert_not_called()
        self.environment.set.assert_not_called()

    def testKeyGenerationDefaultsToGcm(self) -> None:
        """Keep utility and console defaults aligned with application encryption.

        Returns
        -------
        None
            No return value.
        """
        with self.subTest(consumer="utility"):
            self.assertIs(
                signature(SecureKeyGenerator.generate).parameters["cipher"].default,
                Cipher.AES_256_GCM,
            )
        with (
            self.subTest(consumer="command"),
            patch(
                "orionis.console.commands.support.key_generate.Env",
                self.environment,
            ),
            patch.object(
                SecureKeyGenerator,
                "generate",
                return_value="base64:generated",
            ) as generate,
        ):
            self.environment.set.return_value = True
            app = SimpleNamespace(config=Mock(return_value=None))
            self.assertEqual(KeyGenerateCommand().handle(app, Mock()), 0)
            generate.assert_called_once_with(Cipher.AES_256_GCM)
            self.environment.set.assert_called_once_with("APP_KEY", "base64:generated")
