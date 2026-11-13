"""Generate cryptographically secure application secret keys."""

from __future__ import annotations
import os
import base64
from typing import ClassVar
from orionis.foundation.config.app.enums.ciphers import Cipher


class SecureKeyGenerator:
    """Generate cryptographically secure application secret keys."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    # Mapping of cipher modes to their respective key sizes in bytes
    KEY_SIZES: ClassVar[dict[Cipher, int]] = {
        Cipher.AES_128_CBC: 16,
        Cipher.AES_256_CBC: 32,
        Cipher.AES_128_GCM: 16,
        Cipher.AES_256_GCM: 32,
    }
    """Mapping of cipher modes to their respective key sizes in bytes."""

    @staticmethod
    def generate(cipher: str | Cipher = Cipher.AES_256_GCM) -> str:
        """
        Generate a Laravel-compatible APP_KEY.

        Parameters
        ----------
        cipher : str or orionis.foundation.config.app.Cipher
            Cipher used to select key length; default to AES-256-GCM. Legacy
            CBC identifiers remain accepted by this key utility only.

        Returns
        -------
        str
            A base64-encoded key string formatted like Laravel's APP_KEY.

        Raises
        ------
        ValueError
            If the cipher does not name a supported algorithm.
        """
        # Prepare string of valid cipher options for error messages
        str_options = ", ".join(c.value for c in SecureKeyGenerator.KEY_SIZES)

        # Convert string cipher input to Cipher enum if needed
        if isinstance(cipher, str):
            try:
                cipher_enum = Cipher(cipher)
            except ValueError:
                error_msg = (  # NOSONAR(S1110) - Preserve multiline grouping.
                    f"Cipher '{cipher}' is not supported. Options: {str_options}"
                )
                raise ValueError(error_msg) from None
        else:
            cipher_enum = cipher

        # Validate that the cipher is supported
        if cipher_enum not in SecureKeyGenerator.KEY_SIZES:
            error_msg = (
                f"Cipher '{cipher_enum}' is not supported. Options: {str_options}"
            )
            raise ValueError(error_msg)

        # Generate random key with appropriate length for the cipher
        key_length = SecureKeyGenerator.KEY_SIZES[cipher_enum]
        key = os.urandom(key_length)
        return f"base64:{base64.b64encode(key).decode('utf-8')}"
