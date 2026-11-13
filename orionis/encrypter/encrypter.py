# ruff: noqa: TC001
# Keep the application contract available for runtime dependency injection.
"""Encrypt and decrypt application payloads using configured cipher keys."""

import base64
import os
from typing import ClassVar
import msgspec
import msgspec.json as _msjson
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from orionis.foundation.config.app.enums.ciphers import _AUTHENTICATED_CIPHERS
from orionis.foundation.contracts.application import IApplication
from orionis.encrypter.contracts.encrypter import IEncrypter


class _Payload(msgspec.Struct, gc=False):
    """
    Represent serialized encryption payload components.

    Attributes
    ----------
    iv : str
        Base64-encoded initialization vector.
    value : str
        Base64-encoded encrypted value.
    tag : str | None
        Base64-encoded authentication tag; a missing tag is always rejected.
    cipher : str
        Cipher identifier used for encryption.
    """

    iv: str
    value: str
    tag: str | None
    cipher: str


_PAYLOAD_DECODER = _msjson.Decoder(_Payload)
"""Payload decoder used by ``encrypter``."""


class Encrypter(IEncrypter):
    """Encrypt and decrypt application payloads using configured cipher keys."""

    __slots__ = ("_aesgcm", "cipher", "key")
    """Use __slots__ to prevent dynamic attribute creation and reduce memory usage."""

    # Constants for key sizes, IV sizes, tag sizes, and supported ciphers
    AES_128_KEY_SIZE = 16
    """Required key length in bytes for the AES-128 cipher variants."""
    AES_256_KEY_SIZE = 32
    """Required key length in bytes for the AES-256 cipher variants."""
    CBC_IV_SIZE = 16
    """Retain the legacy CBC IV size; unauthenticated CBC is not accepted."""
    GCM_IV_SIZE = 12
    """Nonce length in bytes for GCM mode."""
    GCM_TAG_SIZE = 16
    """Authentication-tag length in bytes for GCM mode."""
    PKCS7_BLOCK_SIZE = 16
    """Retain the legacy padding size for callers describing old payloads."""
    SUPPORTED_CIPHERS: ClassVar[frozenset[str]] = _AUTHENTICATED_CIPHERS
    """Authenticated AES cipher identifiers accepted for application values."""

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialize the encrypter with application configuration.

        Parameters
        ----------
        app : orionis.IApplication
            The application instance providing configuration access.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        TypeError
            If the application key is not normalized immutable bytes.
        ValueError
            If the cipher is not supported or key length is invalid.
        """
        # Get configuration values from application
        self.key: bytes = app.config("app.key")
        """Normalized immutable application key used by the configured cipher."""
        self.cipher: str = app.config("app.cipher")
        """Configured cipher identifier from the supported catalogue."""

        # Validate cipher is supported
        if (
            not isinstance(self.cipher, str)
            or self.cipher not in self.SUPPORTED_CIPHERS
        ):
            error_msg = (
                f"Cipher '{self.cipher}' not supported. "
                f"Use one of: {self.SUPPORTED_CIPHERS}"
            )
            raise ValueError(error_msg)

        # Validate key length according to cipher requirements
        if not isinstance(self.key, bytes):
            error_msg = "Application key must be normalized bytes"
            raise TypeError(error_msg)
        key_len = len(self.key)
        if self.cipher.startswith("AES-128") and key_len != self.AES_128_KEY_SIZE:
            error_msg = f"Key must be {self.AES_128_KEY_SIZE} bytes for AES-128"
            raise ValueError(error_msg)
        if self.cipher.startswith("AES-256") and key_len != self.AES_256_KEY_SIZE:
            error_msg = f"Key must be {self.AES_256_KEY_SIZE} bytes for AES-256"
            raise ValueError(error_msg)

        self._aesgcm = AESGCM(self.key)
        """Reusable authenticated cipher with no mutable per-operation state."""

    def encrypt(
        self,
        plaintext: str,
    ) -> str:
        """
        Encrypt plaintext using the configured cipher algorithm.

        Parameters
        ----------
        plaintext : str
            The text to encrypt.

        Returns
        -------
        str
            Base64-encoded encrypted payload containing IV, value, tag, and cipher.

        Raises
        ------
        TypeError
            If plaintext is not a string.
        ValueError
            If plaintext is empty or has encoding issues.
        RuntimeError
            If encryption fails.
        """
        if not isinstance(plaintext, str):
            error_msg = "Plaintext must be a string"
            raise TypeError(error_msg)

        if not plaintext:
            error_msg = "Plaintext cannot be empty"
            raise ValueError(error_msg)

        try:
            # Convert plaintext to UTF-8 bytes for encryption
            data = plaintext.encode("utf-8")
        except UnicodeEncodeError as e:
            error_msg = f"UTF-8 encoding error: {e}"
            raise ValueError(error_msg) from e

        try:
            return self.__encryptGCM(data)
        except Exception as e:
            error_msg = "Encryption failed"
            raise RuntimeError(error_msg) from e

    def decrypt(
        self,
        payload: str,
    ) -> str:
        """
        Decrypt an encrypted payload using the configured cipher algorithm.

        Parameters
        ----------
        payload : str
            Base64-encoded encrypted payload containing IV, value, tag, and cipher.

        Returns
        -------
        str
            The decrypted plaintext as a UTF-8 string.

        Raises
        ------
        TypeError
            If payload is not a string.
        ValueError
            If payload is empty or invalid.
        RuntimeError
            If decryption fails.
        """
        if not isinstance(payload, str):
            error_msg = "Payload must be a string"
            raise TypeError(error_msg)

        if not payload:
            error_msg = "Payload cannot be empty"
            raise ValueError(error_msg)

        # Decode and validate the payload structure
        parsed = self.__decodePayload(payload)
        cipher, iv, value, tag = self.__extractPayloadData(parsed)

        # Validate cipher compatibility and IV size
        self.__validateCipherMatch(cipher)
        self.__validateIvSize(iv)

        # Perform the actual decryption
        return self.__performDecryption(value, iv, tag)

    def __decodePayload(
        self,
        payload: str,
    ) -> _Payload:
        """
        Decode base64 payload and parse as typed _Payload struct.

        Parameters
        ----------
        payload : str
            Base64-encoded JSON payload string to decode.

        Returns
        -------
        orionis.encrypter.encrypter._Payload
            Decoded and schema-validated payload struct.

        Raises
        ------
        ValueError
            If payload cannot be decoded or parsed as JSON.
        """
        try:
            raw = base64.b64decode(payload, validate=True)
            return _PAYLOAD_DECODER.decode(raw)
        except (msgspec.DecodeError, base64.binascii.Error) as e:
            error_msg = f"Invalid payload: {e}"
            raise ValueError(error_msg) from e

    def __extractPayloadData(
        self,
        data: _Payload,
    ) -> tuple[str, bytes, bytes, bytes | None]:
        """
        Extract payload fields, base64-decoding binary values.

        Parameters
        ----------
        data : orionis.encrypter.encrypter._Payload
            Parsed payload struct (fields already validated by msgspec).

        Returns
        -------
        tuple[str, bytes, bytes, bytes | None]
            Tuple containing (cipher, iv, value, tag) where tag may be None.

        Raises
        ------
        ValueError
            If base64 decoding of any field fails.
        """
        try:
            iv = base64.b64decode(data.iv, validate=True)
            value = base64.b64decode(data.value, validate=True)
            tag = base64.b64decode(data.tag, validate=True) if data.tag else None
            return data.cipher, iv, value, tag
        except base64.binascii.Error as e:
            error_msg = f"Error decoding payload data: {e}"
            raise ValueError(error_msg) from e

    def __validateCipherMatch(
        self,
        cipher: str,
    ) -> None:
        """
        Validate that payload cipher matches the configured cipher.

        Parameters
        ----------
        cipher : str
            The cipher algorithm name from the payload.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If the payload cipher does not match the configured cipher.
        """
        # Check cipher compatibility between payload and configuration
        if cipher != self.cipher:
            error_msg = (
                f"Payload cipher '{cipher}' does not match "
                f"configured cipher '{self.cipher}'"
            )
            raise ValueError(error_msg)

    def __validateIvSize(
        self,
        iv: bytes,
    ) -> None:
        """
        Validate that the IV size matches the configured cipher requirements.

        Parameters
        ----------
        iv : bytes
            The initialization vector bytes to validate.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If IV size does not match the cipher requirements.
        """
        if len(iv) != self.GCM_IV_SIZE:
            error_msg = (
                f"Invalid IV for GCM: expected {self.GCM_IV_SIZE} bytes, "
                f"received {len(iv)}"
            )
            raise ValueError(error_msg)

    def __performDecryption(
        self,
        value: bytes,
        iv: bytes,
        tag: bytes | None,
    ) -> str:
        """
        Perform decryption based on the configured cipher mode.

        Parameters
        ----------
        value : bytes
            The encrypted data to decrypt.
        iv : bytes
            The initialization vector used during encryption.
        tag : bytes | None
            The authentication tag; None is rejected before decryption.

        Returns
        -------
        str
            The decrypted plaintext as a UTF-8 string.

        Raises
        ------
        RuntimeError
            If tag validation, cryptographic decryption, or UTF-8 decoding fails.
        """
        try:
            if tag is None:
                error_msg = "Tag required for GCM mode"
                raise ValueError(error_msg)
            if len(tag) != self.GCM_TAG_SIZE:
                error_msg = (
                    f"Invalid tag: expected {self.GCM_TAG_SIZE} bytes, "
                    f"received {len(tag)}"
                )
                raise ValueError(error_msg)
            return self.__decryptGCM(value, iv, tag).decode("utf-8")

        except Exception as e:
            error_msg = "Decryption failed"
            raise RuntimeError(error_msg) from e

    def __encryptGCM(
        self,
        data: bytes,
    ) -> str:
        """
        Encrypt data using AES-GCM mode with authentication.

        Parameters
        ----------
        data : bytes
            The raw data to encrypt.

        Returns
        -------
        str
            Base64-encoded JSON payload containing IV, encrypted value, tag, and cipher.

        Raises
        ------
        Exception
            Original failure if GCM encryption or payload encoding fails.
        """
        iv = os.urandom(self.GCM_IV_SIZE)
        encrypted = self._aesgcm.encrypt(iv, data, None)
        value, tag = encrypted[: -self.GCM_TAG_SIZE], encrypted[-self.GCM_TAG_SIZE :]
        payload = _Payload(
            iv=base64.b64encode(iv).decode(),
            value=base64.b64encode(value).decode(),
            tag=base64.b64encode(tag).decode(),
            cipher=self.cipher,
        )
        return base64.b64encode(_msjson.encode(payload)).decode()

    def __decryptGCM(
        self,
        value: bytes,
        iv: bytes,
        tag: bytes | None,
    ) -> bytes:
        """
        Decrypt GCM-encrypted data using AESGCM with authentication tag.

        Parameters
        ----------
        value : bytes
            The encrypted ciphertext to decrypt.
        iv : bytes
            The initialization vector used during encryption.
        tag : bytes | None
            The authentication tag for GCM mode verification.

        Returns
        -------
        bytes
            The decrypted plaintext as raw bytes.

        Raises
        ------
        ValueError
            If tag is None.
        cryptography.exceptions.InvalidTag
            If GCM authentication fails.
        Exception
            Original failure if the configured primitive cannot decrypt.
        """
        if tag is None:
            error_msg = "Tag required for GCM decryption"
            raise ValueError(error_msg)
        return self._aesgcm.decrypt(iv, value + tag, None)
