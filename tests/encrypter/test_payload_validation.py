# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Reject malformed encodings and unnormalized encryption configuration."""

import base64
import msgspec.json as msjson
from cryptography.exceptions import InvalidTag
from orionis.encrypter import Encrypter
from orionis.test import TestCase
from tests.encrypter.test_encrypter import (
    _StubApp,
    make_encrypter,
    to_base64,
)


class TestEncryptionInputValidation(TestCase):
    """Protect the ciphertext boundary before cryptographic operations."""

    def testRejectsUnauthenticatedCbcConfiguration(self) -> None:
        """Reject legacy CBC before an instance can encrypt or decrypt data.

        Returns
        -------
        None
            No return value.
        """
        for cipher in ("AES-128-CBC", "AES-256-CBC"):
            with self.subTest(cipher=cipher), self.assertRaises(ValueError):
                make_encrypter(cipher)

    def testAuthenticatesEveryGcmBinaryField(self) -> None:
        """Reject independent nonce, ciphertext and tag changes for both keys.

        Returns
        -------
        None
            No return value.
        """
        for cipher in ("AES-128-GCM", "AES-256-GCM"):
            encrypter = make_encrypter(cipher)
            envelope = msjson.decode(base64.b64decode(encrypter.encrypt("123")))
            for field in ("iv", "value", "tag"):
                with self.subTest(cipher=cipher, field=field):
                    changed = dict(envelope)
                    binary = bytearray(base64.b64decode(changed[field]))
                    binary[0] ^= 1
                    changed[field] = to_base64(binary)
                    with self.assertRaises(RuntimeError) as caught:
                        encrypter.decrypt(to_base64(msjson.encode(changed)))
                    self.assertEqual(str(caught.exception), "Decryption failed")
                    self.assertIsInstance(caught.exception.__cause__, InvalidTag)

    def testRejectsIgnoredCharactersInEveryBase64Layer(self) -> None:
        """Reject nonalphabet bytes instead of silently accepting altered tokens.

        Returns
        -------
        None
            No return value.
        """
        encrypter = make_encrypter("AES-256-GCM")
        token = encrypter.encrypt("strict encoding")
        envelope = msjson.decode(base64.b64decode(token))
        for field in ("outer", "iv", "value", "tag"):
            with self.subTest(field=field):
                if field == "outer":
                    malformed = "!" + token
                else:
                    changed = dict(envelope)
                    changed[field] = "!" + changed[field]
                    malformed = to_base64(msjson.encode(changed))
                with self.assertRaises(ValueError):
                    encrypter.decrypt(malformed)

    def testRejectsUnnormalizedKeysForEveryCipher(self) -> None:
        """Require immutable bytes before creating either authenticated cipher.

        Returns
        -------
        None
            No return value.
        """
        for cipher in sorted(Encrypter.SUPPORTED_CIPHERS):
            length = 16 if cipher.startswith("AES-128") else 32
            for key in ("k" * length, bytearray(b"k" * length), None, 42):
                with (
                    self.subTest(cipher=cipher, key_type=type(key).__name__),
                    self.assertRaises(TypeError),
                ):
                    Encrypter(_StubApp(key, cipher))

    def testRejectsInvalidCipherTypesAsConfigurationErrors(self) -> None:
        """Reject unhashable cipher values with the documented configuration error.

        Returns
        -------
        None
            No return value.
        """
        for cipher in ([], {}, None, 42):
            with (
                self.subTest(cipher_type=type(cipher).__name__),
                self.assertRaises(ValueError),
            ):
                Encrypter(_StubApp(b"k" * 32, cipher))
