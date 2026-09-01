import base64
import os
from typing import ClassVar
import msgspec
import msgspec.json as _msjson
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from orionis.foundation.config.app.enums.ciphers import Cipher as OrionisCipher
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
        Base64-encoded authentication tag when using AEAD modes.
    cipher : str
        Cipher identifier used for encryption.
    """

    iv: str
    value: str
    tag: str | None
    cipher: str

class Encrypter(IEncrypter):

    # ruff: noqa: TC001

    # Use __slots__ to prevent dynamic attribute creation and reduce memory usage
    __slots__ = ("_aesgcm", "_is_gcm", "cipher", "key")

    # Constants for key sizes, IV sizes, tag sizes, and supported ciphers
    AES_128_KEY_SIZE = 16
    AES_256_KEY_SIZE = 32
    CBC_IV_SIZE = 16
    GCM_IV_SIZE = 12
    GCM_TAG_SIZE = 16
    PKCS7_BLOCK_SIZE = 16
    SUPPORTED_CIPHERS: ClassVar[frozenset[str]] = frozenset(
        cipher.value for cipher in OrionisCipher
    )

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialize the encrypter with application configuration.

        Parameters
        ----------
        app : IApplication
            The application instance providing configuration access.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If the cipher is not supported or key length is invalid.
        """
        # Get configuration values from application
        self.key: bytes = app.config("app.key")
        self.cipher: str = app.config("app.cipher")

        # Validate cipher is supported
        if self.cipher not in self.SUPPORTED_CIPHERS:
            error_msg = (
                f"Cipher '{self.cipher}' not supported. "
                f"Use one of: {self.SUPPORTED_CIPHERS}"
            )
            raise ValueError(error_msg)

        # Validate key length according to cipher requirements
        key_len = len(self.key)
        if self.cipher.startswith("AES-128") and key_len != self.AES_128_KEY_SIZE:
            error_msg = f"Key must be {self.AES_128_KEY_SIZE} bytes for AES-128"
            raise ValueError(error_msg)
        if self.cipher.startswith("AES-256") and key_len != self.AES_256_KEY_SIZE:
            error_msg = f"Key must be {self.AES_256_KEY_SIZE} bytes for AES-256"
            raise ValueError(error_msg)

        # Precompute mode flag to avoid repeated substring scans
        self._is_gcm: bool = "GCM" in self.cipher
        # Cache AESGCM instance to avoid per-call key schedule overhead
        self._aesgcm: AESGCM | None = AESGCM(self.key) if self._is_gcm else None

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
            # Choose encryption method based on precomputed mode flag
            if self._is_gcm:
                return self.__encryptGCM(data)
            return self.__encryptCBC(data)
        except Exception as e:
            error_msg = f"Error during encryption: {e}"
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
        _Payload
            Decoded and schema-validated payload struct.

        Raises
        ------
        ValueError
            If payload cannot be decoded or parsed as JSON.
        """
        try:
            raw = base64.b64decode(payload)
            return _msjson.decode(raw, type=_Payload)
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
        data : _Payload
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
            iv = base64.b64decode(data.iv)
            value = base64.b64decode(data.value)
            tag = base64.b64decode(data.tag) if data.tag else None
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
            This method validates compatibility and returns None.

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
            This method validates IV size and returns None.

        Raises
        ------
        ValueError
            If IV size does not match the cipher requirements.
        """
        if self._is_gcm:
            if len(iv) != self.GCM_IV_SIZE:
                error_msg = (
                    f"Invalid IV for GCM: expected {self.GCM_IV_SIZE} bytes, "
                    f"received {len(iv)}"
                )
                raise ValueError(error_msg)
        elif len(iv) != self.CBC_IV_SIZE:
            error_msg = (
                f"Invalid IV for CBC: expected {self.CBC_IV_SIZE} bytes, "
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
            The authentication tag for GCM mode, None for CBC mode.

        Returns
        -------
        str
            The decrypted plaintext as a UTF-8 string.

        Raises
        ------
        ValueError
            If tag requirements are not met for GCM mode.
        RuntimeError
            If decryption fails for any reason.
        """
        try:

            # Handle GCM mode decryption with tag validation
            if self._is_gcm:
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

            # Handle CBC mode decryption
            return self.__decryptCBC(value, iv).decode("utf-8")

        except Exception as e:

            error_msg = f"Error during decryption: {e}"
            raise RuntimeError(error_msg) from e

    def __encryptCBC(
        self,
        data: bytes,
    ) -> str:
        """
        Encrypt data using AES-CBC with PKCS7 padding.

        Parameters
        ----------
        data : bytes
            The raw data to encrypt.

        Returns
        -------
        str
            Base64-encoded JSON payload containing IV, encrypted value, and cipher.

        Raises
        ------
        RuntimeError
            If CBC encryption fails.
        """
        try:

            # Generate random IV for CBC mode
            iv = os.urandom(self.CBC_IV_SIZE)
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv), # NOSONAR
            )
            encryptor = cipher.encryptor()

            # Apply PKCS7 padding to align data to block size
            pad_len = self.PKCS7_BLOCK_SIZE - (len(data) % self.PKCS7_BLOCK_SIZE)
            data = data + bytes([pad_len] * pad_len)

            # Perform encryption
            ct = encryptor.update(data) + encryptor.finalize()

            # Build and serialize payload with msgspec (no intermediate dict)
            payload = _Payload(
                iv=base64.b64encode(iv).decode(),
                value=base64.b64encode(ct).decode(),
                tag=None,
                cipher=self.cipher,
            )
            return base64.b64encode(_msjson.encode(payload)).decode()

        except Exception as e:

            # Raise error if encryption fails
            error_msg = f"Error in CBC encryption: {e}"
            raise RuntimeError(error_msg) from e

    def __decryptCBC(
        self,
        ct: bytes,
        iv: bytes,
    ) -> bytes:
        """
        Decrypt CBC-encrypted data and remove PKCS7 padding.

        Parameters
        ----------
        ct : bytes
            The encrypted ciphertext to decrypt.
        iv : bytes
            The initialization vector used during encryption.

        Returns
        -------
        bytes
            The decrypted plaintext with padding removed.

        Raises
        ------
        ValueError
            If decrypted data is empty or padding is invalid.
        RuntimeError
            If CBC decryption fails.
        """
        try:

            # Create cipher instance and decryptor for CBC mode
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv), # NOSONAR
            )
            decryptor = cipher.decryptor()

            # Perform decryption
            data = decryptor.update(ct) + decryptor.finalize()

            # Validate decrypted data is not empty
            if len(data) == 0:
                error_msg = "Decrypted data is empty"
                raise ValueError(error_msg)

            # Extract padding length from last byte
            pad_len = data[-1]

            # Validate padding length is within acceptable range
            if pad_len == 0 or pad_len > self.PKCS7_BLOCK_SIZE:
                error_msg = f"Invalid PKCS7 padding length: {pad_len}"
                raise ValueError(error_msg)

            # Verify padding bytes with bulk C-level comparison
            if data[-pad_len:] != bytes([pad_len] * pad_len):
                error_msg = "Corrupted PKCS7 padding"
                raise ValueError(error_msg)

            # Return data with padding removed
            return data[:-pad_len]

        except ValueError:

            # Re-raise ValueErrors for padding issues
            raise
        except Exception as e:

            # Raise error if decryption fails
            error_msg = f"Error in CBC decryption: {e}"
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
        RuntimeError
            If GCM encryption fails.
        """
        try:

            # Generate random IV for GCM mode
            iv = os.urandom(self.GCM_IV_SIZE)
            ct = self._aesgcm.encrypt(iv, data, None)

            # Separate ciphertext and tag (last bytes according to GCM_TAG_SIZE)
            value, tag = ct[:-self.GCM_TAG_SIZE], ct[-self.GCM_TAG_SIZE:]

            # Build and serialize payload with msgspec (no intermediate dict)
            payload = _Payload(
                iv=base64.b64encode(iv).decode(),
                value=base64.b64encode(value).decode(),
                tag=base64.b64encode(tag).decode(),
                cipher=self.cipher,
            )
            return base64.b64encode(_msjson.encode(payload)).decode()

        except Exception as e:

            # Raise error if encryption fails
            error_msg = f"Error in GCM encryption: {e}"
            raise RuntimeError(error_msg) from e

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
            If tag is None or GCM verification fails.
        RuntimeError
            If GCM decryption fails for any other reason.
        """
        try:

            # Validate authentication tag is provided
            if tag is None:
                error_msg = "Tag required for GCM decryption"
                raise ValueError(error_msg)

            # Use cached AESGCM instance (key schedule computed once in __init__)
            return self._aesgcm.decrypt(iv, value + tag, None)

        except ValueError:

            # Re-raise ValueError for tag validation issues
            raise
        except Exception as e:

            # Raise error if decryption fails
            error_msg = f"Error in GCM decryption: {e}"
            raise RuntimeError(error_msg) from e
