import base64
from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.foundation.config.app.enums.ciphers import Cipher
from orionis.test import TestCase

# Prefix every generated key is expected to carry.
_KEY_PREFIX: str = "base64:"

# ---------------------------------------------------------------------------
# TestSecureKeyGeneratorCatalogue
# ---------------------------------------------------------------------------

class TestSecureKeyGeneratorCatalogue(TestCase):

    def testCoversEveryDeclaredCipher(self) -> None:
        """
        Map every declared cipher to a key size.

        Validates that no supported cipher is left without an entry, which
        would make key generation fail at runtime.
        """
        self.assertEqual(set(SecureKeyGenerator.KEY_SIZES), set(Cipher))

    def testDeclaresTheKeySizeRequiredByEachCipher(self) -> None:
        """
        Declare the byte length required by each cipher variant.

        Validates that 128-bit modes map to 16 bytes and 256-bit modes to
        32 bytes, as expected by the encrypter.
        """
        self.assertEqual(
            SecureKeyGenerator.KEY_SIZES,
            {
                Cipher.AES_128_CBC: 16,
                Cipher.AES_256_CBC: 32,
                Cipher.AES_128_GCM: 16,
                Cipher.AES_256_GCM: 32,
            },
        )

# ---------------------------------------------------------------------------
# TestSecureKeyGeneratorOutput
# ---------------------------------------------------------------------------

class TestSecureKeyGeneratorOutput(TestCase):

    def testDefaultsToTheAes256CbcCipher(self) -> None:
        """
        Generate a 32 byte key when no cipher is supplied.

        Validates the documented default, which must stay aligned with the
        cipher configured by a freshly scaffolded application.
        """
        generated = SecureKeyGenerator.generate()
        payload = base64.b64decode(generated.removeprefix(_KEY_PREFIX))
        self.assertEqual(len(payload), 32)

    def testProducesADecodableKeyForEveryCipher(self) -> None:
        """
        Produce a prefixed, decodable key for every supported cipher.

        Validates the Laravel compatible ``base64:`` envelope and that the
        decoded payload matches the declared key size.
        """
        for cipher, size in SecureKeyGenerator.KEY_SIZES.items():
            generated = SecureKeyGenerator.generate(cipher)
            self.assertTrue(generated.startswith(_KEY_PREFIX))
            payload = base64.b64decode(
                generated.removeprefix(_KEY_PREFIX),
                validate=True,
            )
            self.assertEqual(len(payload), size)

    def testAcceptsTheCipherAsAPlainString(self) -> None:
        """
        Accept the cipher expressed as its canonical string value.

        Validates the branch used when the cipher arrives straight from an
        environment variable instead of the enumeration.
        """
        for cipher, size in SecureKeyGenerator.KEY_SIZES.items():
            generated = SecureKeyGenerator.generate(cipher.value)
            payload = base64.b64decode(generated.removeprefix(_KEY_PREFIX))
            self.assertEqual(len(payload), size)

    def testProducesADifferentKeyOnEveryCall(self) -> None:
        """
        Produce cryptographically distinct keys across invocations.

        Validates that the generator draws fresh randomness instead of
        reusing a cached or seeded value.
        """
        generated = {SecureKeyGenerator.generate() for _ in range(25)}
        self.assertEqual(len(generated), 25)

# ---------------------------------------------------------------------------
# TestSecureKeyGeneratorRejections
# ---------------------------------------------------------------------------

class TestSecureKeyGeneratorRejections(TestCase):

    def testRejectsAnUnknownCipherName(self) -> None:
        """
        Raise ValueError when the cipher name is not recognised.

        Validates that the message lists the supported options so the
        misconfiguration can be corrected immediately.
        """
        with self.assertRaises(ValueError) as ctx:
            SecureKeyGenerator.generate("AES-512-CBC")
        message = str(ctx.exception)
        self.assertIn("AES-512-CBC", message)
        self.assertIn("AES-256-CBC", message)

    def testRejectsAnEmptyCipherName(self) -> None:
        """
        Raise ValueError when the cipher name is an empty string.

        Validates that a blank environment variable cannot silently fall
        back to the default cipher.
        """
        with self.assertRaises(ValueError):
            SecureKeyGenerator.generate("")

    def testRejectsACipherOutsideTheSizeCatalogue(self) -> None:
        """
        Raise ValueError when a non-string cipher has no declared size.

        Validates the guard protecting the key size lookup from arbitrary
        objects that bypass the string conversion branch.
        """
        with self.assertRaises(ValueError) as ctx:
            SecureKeyGenerator.generate(object())
        self.assertIn("is not supported", str(ctx.exception))

# ---------------------------------------------------------------------------
# TestSecureKeyGeneratorLayout
# ---------------------------------------------------------------------------

class TestSecureKeyGeneratorLayout(TestCase):

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots for a generator that holds no state.

        Validates that the utility keeps its whole catalogue at class
        level instead of per instance.
        """
        self.assertEqual(SecureKeyGenerator.__slots__, ())

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep instances free of a dictionary.

        Validates that an accidental instantiation cannot be used to
        shadow the declared key sizes.
        """
        self.assertFalse(hasattr(SecureKeyGenerator(), "__dict__"))
