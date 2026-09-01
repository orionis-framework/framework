import base64
import msgspec.json as msjson
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.encrypter.encrypter import Encrypter
from orionis.test import TestCase

# Deterministic keys: 16 bytes for the AES-128 family, 32 for the AES-256 one.
_KEY_16: bytes = b"\x4b" * 16
_KEY_32: bytes = b"\x9f" * 32

# Fixed initialisation vectors used to forge payloads by hand.
_CBC_IV: bytes = b"\x11" * 16
_GCM_IV: bytes = b"\x22" * 12

# Every cipher accepted by the encrypter.
_CIPHERS: tuple[str, ...] = (
    "AES-128-CBC",
    "AES-128-GCM",
    "AES-256-CBC",
    "AES-256-GCM",
)


class _StubApp:
    """Application double exposing only the two configuration keys read."""

    __slots__ = ("_cipher", "_key")

    def __init__(self, key: bytes, cipher: str) -> None:
        self._key = key
        self._cipher = cipher

    def config(self, path: str) -> object:
        """
        Return the configuration value bound to the requested path.

        Parameters
        ----------
        path : str
            Dotted configuration path requested by the encrypter.

        Returns
        -------
        object
            The configured key or cipher, or None for any other path.
        """
        if path == "app.key":
            return self._key
        if path == "app.cipher":
            return self._cipher
        return None


def key_for(cipher: str) -> bytes:
    """
    Return the key matching the key size demanded by a cipher name.

    Parameters
    ----------
    cipher : str
        Name of the cipher the key is built for.

    Returns
    -------
    bytes
        A 16-byte key for AES-128 variants, a 32-byte one otherwise.
    """
    return _KEY_16 if cipher.startswith("AES-128") else _KEY_32


def make_encrypter(cipher: str) -> Encrypter:
    """
    Build an encrypter configured with a valid key for the given cipher.

    Parameters
    ----------
    cipher : str
        Name of the cipher to configure.

    Returns
    -------
    Encrypter
        A ready-to-use encrypter instance.
    """
    return Encrypter(_StubApp(key_for(cipher), cipher))


def to_base64(data: bytes) -> str:
    """
    Encode raw bytes as an ASCII base64 string.

    Parameters
    ----------
    data : bytes
        Raw bytes to encode.

    Returns
    -------
    str
        The base64 representation of the given bytes.
    """
    return base64.b64encode(data).decode()


def encode_payload(cipher: str, iv: str, value: str, tag: str | None) -> str:
    """
    Build the base64-wrapped JSON envelope consumed by decrypt().

    Parameters
    ----------
    cipher : str
        Cipher name stored in the envelope.
    iv : str
        Already encoded initialisation vector field.
    value : str
        Already encoded ciphertext field.
    tag : str | None
        Already encoded authentication tag, or None for CBC payloads.

    Returns
    -------
    str
        A payload string shaped exactly like the one encrypt() returns.
    """
    envelope = {"iv": iv, "value": value, "tag": tag, "cipher": cipher}
    return to_base64(msjson.encode(envelope))


def cbc_payload_from_raw(raw: bytes) -> str:
    """
    Wrap unpadded bytes into an AES-128-CBC payload without PKCS7 padding.

    Parameters
    ----------
    raw : bytes
        Block-aligned bytes encrypted verbatim, so the decrypter observes
        whatever padding byte the caller planted in the last position.

    Returns
    -------
    str
        A payload string accepted by decrypt() up to the padding check.
    """
    algorithm = algorithms.AES(_KEY_16)
    encryptor = Cipher(algorithm, modes.CBC(_CBC_IV)).encryptor()
    ciphertext = encryptor.update(raw) + encryptor.finalize()
    return encode_payload(
        "AES-128-CBC",
        to_base64(_CBC_IV),
        to_base64(ciphertext),
        None,
    )


class TestEncrypterDefinition(TestCase):

    def testExposesTheAesSizeConstants(self) -> None:
        """
        Publish the byte sizes demanded by every supported mode.

        Validates the key, IV, tag and PKCS7 block constants shared by the
        encryption and the payload validation paths.
        """
        self.assertEqual(Encrypter.AES_128_KEY_SIZE, 16)
        self.assertEqual(Encrypter.AES_256_KEY_SIZE, 32)
        self.assertEqual(Encrypter.CBC_IV_SIZE, 16)
        self.assertEqual(Encrypter.GCM_IV_SIZE, 12)
        self.assertEqual(Encrypter.GCM_TAG_SIZE, 16)
        self.assertEqual(Encrypter.PKCS7_BLOCK_SIZE, 16)

    def testAdvertisesTheSupportedCiphersAsAFrozenSet(self) -> None:
        """
        Advertise exactly the four AES variants the service accepts.

        Validates the immutable catalogue used to reject unknown ciphers.
        """
        self.assertIsInstance(Encrypter.SUPPORTED_CIPHERS, frozenset)
        self.assertEqual(Encrypter.SUPPORTED_CIPHERS, frozenset(_CIPHERS))

    def testImplementsTheEncrypterContract(self) -> None:
        """
        Satisfy the IEncrypter contract published by the module.

        Validates the type the container binds the service to.
        """
        self.assertIsInstance(make_encrypter("AES-128-CBC"), IEncrypter)

    def testInstancesDoNotCarryAnAttributeDictionary(self) -> None:
        """
        Keep instances free of a per-object attribute dictionary.

        Validates that the declared slots are honoured, which only holds
        while the contract also declares empty slots.
        """
        self.assertFalse(hasattr(make_encrypter("AES-256-GCM"), "__dict__"))


class TestEncrypterInitialisation(TestCase):

    def testReadsKeyAndCipherFromTheApplicationConfiguration(self) -> None:
        """
        Adopt the key and cipher published by the application.

        Validates that no default is injected by the constructor.
        """
        encrypter = make_encrypter("AES-256-CBC")
        self.assertEqual(encrypter.key, _KEY_32)
        self.assertEqual(encrypter.cipher, "AES-256-CBC")

    def testAcceptsEverySupportedCipher(self) -> None:
        """
        Build successfully for each entry of the supported catalogue.

        Validates that the catalogue and the key size rules agree.
        """
        for cipher in _CIPHERS:
            self.assertEqual(make_encrypter(cipher).cipher, cipher)

    def testCbcModeSkipsTheAuthenticatedCipherHelper(self) -> None:
        """
        Leave the AEAD helper unset when a CBC cipher is configured.

        Validates the mode flag precomputed once at construction time.
        """
        encrypter = make_encrypter("AES-128-CBC")
        self.assertFalse(encrypter._is_gcm)
        self.assertIsNone(encrypter._aesgcm)

    def testGcmModeCachesTheAuthenticatedCipherHelper(self) -> None:
        """
        Cache an AESGCM helper when a GCM cipher is configured.

        Validates that the key schedule is computed once per instance.
        """
        encrypter = make_encrypter("AES-256-GCM")
        self.assertTrue(encrypter._is_gcm)
        self.assertIsInstance(encrypter._aesgcm, AESGCM)

    def testRejectsAnUnsupportedCipher(self) -> None:
        """
        Refuse to build when the configured cipher is unknown.

        Validates the guard protecting against unusable configurations.
        """
        with self.assertRaises(ValueError) as ctx:
            Encrypter(_StubApp(_KEY_16, "AES-128-XTS"))
        self.assertIn("not supported", str(ctx.exception))

    def testRejectsKeysThatDoNotMatchTheAes128KeySize(self) -> None:
        """
        Refuse AES-128 keys shorter or longer than sixteen bytes.

        Validates both sides of the key length comparison.
        """
        with self.assertRaises(ValueError) as short_ctx:
            Encrypter(_StubApp(b"too-short", "AES-128-CBC"))
        self.assertIn("16 bytes", str(short_ctx.exception))
        with self.assertRaises(ValueError):
            Encrypter(_StubApp(_KEY_32, "AES-128-GCM"))

    def testRejectsKeysThatDoNotMatchTheAes256KeySize(self) -> None:
        """
        Refuse AES-256 keys shorter or longer than thirty-two bytes.

        Validates both sides of the key length comparison.
        """
        with self.assertRaises(ValueError) as short_ctx:
            Encrypter(_StubApp(_KEY_16, "AES-256-CBC"))
        self.assertIn("32 bytes", str(short_ctx.exception))
        with self.assertRaises(ValueError):
            Encrypter(_StubApp(_KEY_32 + b"\x00", "AES-256-GCM"))


class TestEncrypterEncrypt(TestCase):

    def testRejectsNonStringPlaintext(self) -> None:
        """
        Refuse plaintext values that are not strings.

        Validates the type guard placed before any encoding work.
        """
        encrypter = make_encrypter("AES-128-CBC")
        with self.assertRaises(TypeError):
            encrypter.encrypt(123)  # type: ignore[arg-type]

    def testRejectsEmptyPlaintext(self) -> None:
        """
        Refuse an empty plaintext string.

        Validates the guard that keeps empty payloads out of the cipher.
        """
        encrypter = make_encrypter("AES-256-GCM")
        with self.assertRaises(ValueError):
            encrypter.encrypt("")

    def testRejectsPlaintextThatCannotBeEncodedAsUtf8(self) -> None:
        """
        Refuse plaintext holding an unpaired surrogate character.

        Validates the branch translating encoding failures into ValueError.
        """
        encrypter = make_encrypter("AES-128-CBC")
        with self.assertRaises(ValueError) as ctx:
            encrypter.encrypt("\ud800")
        self.assertIn("UTF-8 encoding error", str(ctx.exception))

    def testCbcPayloadCarriesTheIvAndCipherWithoutTag(self) -> None:
        """
        Emit a CBC envelope with a block-sized IV and a null tag.

        Validates the payload layout produced by the CBC branch.
        """
        encrypter = make_encrypter("AES-256-CBC")
        envelope = msjson.decode(base64.b64decode(encrypter.encrypt("cbc")))
        self.assertEqual(envelope["cipher"], "AES-256-CBC")
        self.assertIsNone(envelope["tag"])
        self.assertEqual(len(base64.b64decode(envelope["iv"])), 16)
        self.assertTrue(base64.b64decode(envelope["value"]))

    def testGcmPayloadCarriesTheAuthenticationTag(self) -> None:
        """
        Emit a GCM envelope with a short IV and a detached tag.

        Validates the payload layout produced by the GCM branch.
        """
        encrypter = make_encrypter("AES-128-GCM")
        envelope = msjson.decode(base64.b64decode(encrypter.encrypt("gcm")))
        self.assertEqual(envelope["cipher"], "AES-128-GCM")
        self.assertEqual(len(base64.b64decode(envelope["iv"])), 12)
        self.assertEqual(len(base64.b64decode(envelope["tag"])), 16)

    def testRepeatedEncryptionsOfTheSameTextDiffer(self) -> None:
        """
        Produce a different payload on every call for the same plaintext.

        Validates that a fresh random IV is drawn per operation.
        """
        encrypter = make_encrypter("AES-256-GCM")
        self.assertNotEqual(encrypter.encrypt("same"), encrypter.encrypt("same"))

    def testWrapsCbcEncryptionFailuresInRuntimeError(self) -> None:
        """
        Surface a runtime error when the CBC primitive cannot be built.

        Validates the failure path of the CBC encryption helper.
        """
        encrypter = make_encrypter("AES-128-CBC")
        encrypter.key = "not-bytes"  # type: ignore[assignment]
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.encrypt("boom")
        self.assertIn("Error in CBC encryption", str(ctx.exception))

    def testWrapsGcmEncryptionFailuresInRuntimeError(self) -> None:
        """
        Surface a runtime error when the AEAD helper is unavailable.

        Validates the failure path of the GCM encryption helper.
        """
        encrypter = make_encrypter("AES-256-GCM")
        encrypter._aesgcm = None
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.encrypt("boom")
        self.assertIn("Error in GCM encryption", str(ctx.exception))


class TestEncrypterDecryptPayloadValidation(TestCase):

    def testRejectsNonStringPayload(self) -> None:
        """
        Refuse payload values that are not strings.

        Validates the type guard placed before any decoding work.
        """
        encrypter = make_encrypter("AES-128-CBC")
        with self.assertRaises(TypeError):
            encrypter.decrypt(42)  # type: ignore[arg-type]

    def testRejectsEmptyPayload(self) -> None:
        """
        Refuse an empty payload string.

        Validates the guard that keeps empty envelopes out of the decoder.
        """
        encrypter = make_encrypter("AES-256-GCM")
        with self.assertRaises(ValueError):
            encrypter.decrypt("")

    def testRejectsPayloadThatIsNotValidBase64(self) -> None:
        """
        Refuse a payload whose outer base64 envelope is malformed.

        Validates the binascii failure branch of the payload decoder.
        """
        encrypter = make_encrypter("AES-256-CBC")
        with self.assertRaises(ValueError) as ctx:
            encrypter.decrypt("abcde")
        self.assertIn("Invalid payload", str(ctx.exception))

    def testRejectsPayloadThatIsNotValidJson(self) -> None:
        """
        Refuse a payload whose decoded bytes are not JSON.

        Validates the decode failure branch of the payload decoder.
        """
        encrypter = make_encrypter("AES-128-CBC")
        with self.assertRaises(ValueError) as ctx:
            encrypter.decrypt(to_base64(b"this-is-not-json"))
        self.assertIn("Invalid payload", str(ctx.exception))

    def testRejectsPayloadMissingRequiredFields(self) -> None:
        """
        Refuse a JSON envelope that omits a mandatory field.

        Validates the schema enforced while decoding the envelope.
        """
        encrypter = make_encrypter("AES-128-CBC")
        incomplete = to_base64(msjson.encode({"iv": to_base64(_CBC_IV)}))
        with self.assertRaises(ValueError) as ctx:
            encrypter.decrypt(incomplete)
        self.assertIn("Invalid payload", str(ctx.exception))

    def testRejectsPayloadFieldsThatAreNotValidBase64(self) -> None:
        """
        Refuse an envelope whose binary fields cannot be decoded.

        Validates the branch reporting malformed inner base64 values.
        """
        encrypter = make_encrypter("AES-128-CBC")
        payload = encode_payload("AES-128-CBC", "a", "", None)
        with self.assertRaises(ValueError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Error decoding payload data", str(ctx.exception))

    def testRejectsPayloadProducedByAnotherCipher(self) -> None:
        """
        Refuse an envelope whose cipher differs from the configured one.

        Validates the compatibility guard between payload and instance.
        """
        source = make_encrypter("AES-128-CBC")
        target = make_encrypter("AES-256-CBC")
        with self.assertRaises(ValueError) as ctx:
            target.decrypt(source.encrypt("mismatch"))
        self.assertIn("does not match", str(ctx.exception))

    def testRejectsCbcPayloadWithAnUnexpectedIvSize(self) -> None:
        """
        Refuse a CBC envelope whose IV is not sixteen bytes long.

        Validates the CBC branch of the IV size guard.
        """
        encrypter = make_encrypter("AES-128-CBC")
        payload = encode_payload(
            "AES-128-CBC",
            to_base64(b"\x00" * 5),
            to_base64(b"\x00" * 16),
            None,
        )
        with self.assertRaises(ValueError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Invalid IV for CBC", str(ctx.exception))

    def testRejectsGcmPayloadWithAnUnexpectedIvSize(self) -> None:
        """
        Refuse a GCM envelope whose IV is not twelve bytes long.

        Validates the GCM branch of the IV size guard.
        """
        encrypter = make_encrypter("AES-128-GCM")
        payload = encode_payload(
            "AES-128-GCM",
            to_base64(b"\x00" * 5),
            to_base64(b"\x00" * 16),
            to_base64(b"\x00" * 16),
        )
        with self.assertRaises(ValueError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Invalid IV for GCM", str(ctx.exception))


class TestEncrypterDecryptFailures(TestCase):

    def testRejectsGcmPayloadWithoutAuthenticationTag(self) -> None:
        """
        Refuse a GCM envelope that carries no authentication tag.

        Validates the guard demanding a tag before touching the cipher.
        """
        encrypter = make_encrypter("AES-128-GCM")
        payload = encode_payload(
            "AES-128-GCM",
            to_base64(_GCM_IV),
            to_base64(b"\x00" * 8),
            None,
        )
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Tag required for GCM mode", str(ctx.exception))

    def testRejectsGcmPayloadWithATagOfTheWrongSize(self) -> None:
        """
        Refuse a GCM envelope whose tag is not sixteen bytes long.

        Validates the tag size guard applied before authentication.
        """
        encrypter = make_encrypter("AES-128-GCM")
        payload = encode_payload(
            "AES-128-GCM",
            to_base64(_GCM_IV),
            to_base64(b"\x00" * 8),
            to_base64(b"\x00" * 4),
        )
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Invalid tag", str(ctx.exception))

    def testRejectsGcmPayloadThatFailsAuthentication(self) -> None:
        """
        Refuse a GCM envelope whose tag does not authenticate the data.

        Validates the failure path of the GCM decryption helper.
        """
        encrypter = make_encrypter("AES-128-GCM")
        payload = encode_payload(
            "AES-128-GCM",
            to_base64(_GCM_IV),
            to_base64(b"\x00" * 8),
            to_base64(b"\x00" * 16),
        )
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Error in GCM decryption", str(ctx.exception))

    def testRejectsGcmDecryptionWithoutTagAtTheHelperLevel(self) -> None:
        """
        Refuse a direct GCM decryption call that omits the tag.

        Validates the defensive guard of the private GCM helper, which the
        public path already shields with its own tag check.
        """
        encrypter = make_encrypter("AES-256-GCM")
        with self.assertRaises(ValueError) as ctx:
            encrypter._Encrypter__decryptGCM(b"\x00" * 8, _GCM_IV, None)
        self.assertIn("Tag required for GCM decryption", str(ctx.exception))

    def testRejectsCbcPayloadThatDecryptsToNothing(self) -> None:
        """
        Refuse a CBC envelope holding an empty ciphertext.

        Validates the guard rejecting empty plaintext before unpadding.
        """
        encrypter = make_encrypter("AES-128-CBC")
        payload = encode_payload("AES-128-CBC", to_base64(_CBC_IV), "", None)
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Decrypted data is empty", str(ctx.exception))

    def testRejectsCbcPaddingLengthOfZero(self) -> None:
        """
        Refuse a CBC plaintext whose trailing padding byte is zero.

        Validates the lower bound of the PKCS7 padding length check.
        """
        encrypter = make_encrypter("AES-128-CBC")
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(cbc_payload_from_raw(b"\x00" * 16))
        self.assertIn("Invalid PKCS7 padding length", str(ctx.exception))

    def testRejectsCbcPaddingLengthAboveTheBlockSize(self) -> None:
        """
        Refuse a CBC plaintext whose padding byte exceeds one block.

        Validates the upper bound of the PKCS7 padding length check.
        """
        encrypter = make_encrypter("AES-128-CBC")
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(cbc_payload_from_raw(b"\xff" * 16))
        self.assertIn("Invalid PKCS7 padding length", str(ctx.exception))

    def testRejectsCbcPaddingWithInconsistentBytes(self) -> None:
        """
        Refuse a CBC plaintext whose padding bytes are not uniform.

        Validates the bulk comparison of the PKCS7 padding block.
        """
        encrypter = make_encrypter("AES-128-CBC")
        raw = b"\x00" * 14 + b"\x01\x02"
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(cbc_payload_from_raw(raw))
        self.assertIn("Corrupted PKCS7 padding", str(ctx.exception))

    def testWrapsCbcDecryptionFailuresInRuntimeError(self) -> None:
        """
        Surface a runtime error when the CBC primitive cannot be built.

        Validates the failure path of the CBC decryption helper.
        """
        encrypter = make_encrypter("AES-128-CBC")
        payload = encrypter.encrypt("boom")
        encrypter.key = "not-bytes"  # type: ignore[assignment]
        with self.assertRaises(RuntimeError) as ctx:
            encrypter.decrypt(payload)
        self.assertIn("Error in CBC decryption", str(ctx.exception))


class TestEncrypterRoundTrip(TestCase):

    def testRecoversPlaintextForEverySupportedCipher(self) -> None:
        """
        Recover the original text after a full cycle in every mode.

        Validates the interoperability of both encryption branches with
        their matching decryption branches.
        """
        for cipher in _CIPHERS:
            encrypter = make_encrypter(cipher)
            self.assertEqual(encrypter.decrypt(encrypter.encrypt(cipher)), cipher)

    def testRecoversPlaintextOfExactlyOneBlock(self) -> None:
        """
        Recover a text whose length matches the PKCS7 block size.

        Validates the boundary where a whole padding block is appended.
        """
        encrypter = make_encrypter("AES-256-CBC")
        original = "a" * 16
        self.assertEqual(encrypter.decrypt(encrypter.encrypt(original)), original)

    def testRecoversASingleCharacter(self) -> None:
        """
        Recover the shortest possible non-empty plaintext.

        Validates the boundary where padding fills almost a whole block.
        """
        encrypter = make_encrypter("AES-128-CBC")
        self.assertEqual(encrypter.decrypt(encrypter.encrypt("x")), "x")

    def testRecoversAMultiBlockPayload(self) -> None:
        """
        Recover a text spanning many cipher blocks.

        Validates streaming of large inputs through both modes.
        """
        encrypter = make_encrypter("AES-256-GCM")
        original = "z" * 4096
        self.assertEqual(encrypter.decrypt(encrypter.encrypt(original)), original)

    def testRecoversMultibyteUnicodeCharacters(self) -> None:
        """
        Recover a text made of multibyte Unicode characters.

        Validates the UTF-8 encode and decode round trip.
        """
        encrypter = make_encrypter("AES-256-CBC")
        original = "こんにちは 你好 مرحبا"
        self.assertEqual(encrypter.decrypt(encrypter.encrypt(original)), original)

    def testRecoversControlAndPunctuationCharacters(self) -> None:
        """
        Recover a text containing newlines, tabs and punctuation.

        Validates that no character is stripped by the envelope encoding.
        """
        encrypter = make_encrypter("AES-128-GCM")
        original = "line1\nline2\tend !@#$%^&*()_+-=[]{}|;':\",./<>?"
        self.assertEqual(encrypter.decrypt(encrypter.encrypt(original)), original)
